import os
import re
import json
import psycopg2
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class Database:
    """
    Connexion à la base market_intelligence.
    Toutes les méthodes utilisent des requêtes paramétrées (aucun SQL brut
    n'est jamais construit à partir d'une chaîne fournie par l'IA ou l'utilisateur).
    """

    COLONNES_COMPLETES = [
        "id", "source", "type", "titre", "link", "date_publication",
        "resume", "date_scraping", "created_at",
    ]
    COLONNES_LISTE = [
        "id", "source", "type", "titre", "link", "date_publication", "resume",
    ]

    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "market_intelligence"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    # ---------- LECTURE ----------

    def get_articles(self, nombre=5, type_filtre=None, mot_cle=None,
                      article_id=None, source=None, date_debut=None, date_fin=None):
        if article_id:
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT {", ".join(self.COLONNES_COMPLETES)}
                    FROM economic_watch_article
                    WHERE id ILIKE %s;
                """, (f"%{article_id}%",))
                return [dict(zip(self.COLONNES_COMPLETES, l)) for l in cur.fetchall()]

        conditions, params = [], []
        if type_filtre:
            conditions.append("type ILIKE %s"); params.append(f"%{type_filtre}%")
        if source:
            conditions.append("source ILIKE %s"); params.append(f"%{source}%")
        if mot_cle:
            conditions.append("(titre ILIKE %s OR resume ILIKE %s)")
            params += [f"%{mot_cle}%", f"%{mot_cle}%"]
        if date_debut:
            conditions.append("date_publication >= %s"); params.append(date_debut)
        if date_fin:
            conditions.append("date_publication <= %s"); params.append(date_fin)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        requete = f"""
            SELECT {", ".join(self.COLONNES_LISTE)}
            FROM economic_watch_article
            {where_clause}
            ORDER BY date_scraping DESC
            LIMIT %s;
        """
        params.append(nombre)
        with self.conn.cursor() as cur:
            cur.execute(requete, params)
            return [dict(zip(self.COLONNES_LISTE, l)) for l in cur.fetchall()]

    def compter_articles(self, type_filtre=None, mot_cle=None, source=None,
                          date_debut=None, date_fin=None):
        conditions, params = [], []
        if type_filtre:
            conditions.append("type ILIKE %s"); params.append(f"%{type_filtre}%")
        if source:
            conditions.append("source ILIKE %s"); params.append(f"%{source}%")
        if mot_cle:
            conditions.append("(titre ILIKE %s OR resume ILIKE %s)")
            params += [f"%{mot_cle}%", f"%{mot_cle}%"]
        if date_debut:
            conditions.append("date_publication >= %s"); params.append(date_debut)
        if date_fin:
            conditions.append("date_publication <= %s"); params.append(date_fin)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM economic_watch_article {where_clause};", params)
            return cur.fetchone()[0]

    # ---------- ÉCRITURE ----------

    def ajouter_article(self, source, type, titre, link=None,
                         date_publication=None, resume=None):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO economic_watch_article
                    (source, type, titre, link, date_publication, resume, date_scraping, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id;
            """, (source, type, titre, link, date_publication, resume))
            self.conn.commit()
            return cur.fetchone()[0]

    def modifier_article(self, article_id, champs: dict):
        """champs : dict des colonnes à modifier (whitelist stricte ci-dessous)."""
        colonnes_autorisees = {"source", "type", "titre", "link", "date_publication", "resume"}
        champs = {k: v for k, v in champs.items() if k in colonnes_autorisees}
        if not champs:
            return 0
        set_clause = ", ".join(f"{k} = %s" for k in champs)
        params = list(champs.values()) + [article_id]
        with self.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE economic_watch_article
                SET {set_clause}
                WHERE id = %s;
            """, params)
            self.conn.commit()
            return cur.rowcount

    def supprimer_article(self, article_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM economic_watch_article WHERE id = %s;", (article_id,))
            self.conn.commit()
            return cur.rowcount

    def fermer(self):
        self.conn.close()


def lire_page_web(url: str, longueur_max: int = 6000) -> str:
    """
    Récupère et extrait le texte principal d'une page web.
    Timeout court + taille limitée pour éviter les abus / pages trop lourdes.
    """
    if not url or not url.startswith(("http://", "https://")):
        return "Erreur : URL invalide ou manquante."

    en_tetes = {"User-Agent": "Mozilla/5.0 (compatible; ArticlesBot/1.0)"}
    try:
        reponse = requests.get(url, headers=en_tetes, timeout=8)
        reponse.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"Erreur lors de la récupération de la page : {e}"

    html = reponse.text

    # Retrait des blocs non pertinents (scripts, styles) avant nettoyage des balises
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Suppression de toutes les balises HTML restantes
    texte = re.sub(r"<[^>]+>", "\n", html)
    # Décodage des entités HTML les plus courantes
    texte = (texte.replace("&nbsp;", " ").replace("&amp;", "&")
                  .replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&quot;", '"').replace("&#39;", "'"))

    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    texte_propre = "\n".join(lignes)

    if len(texte_propre) > longueur_max:
        texte_propre = texte_propre[:longueur_max] + "\n[... contenu tronqué ...]"

    return texte_propre if texte_propre else "Aucun contenu textuel extrait de cette page."


# ---------- Définition des outils exposés au modèle ----------

OUTILS = [
    {"type": "function", "function": {
        "name": "rechercher_articles",
        "description": "Recherche des articles selon différents filtres, ou un article précis par ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {"type": "integer", "description": "Nombre d'articles à retourner (défaut 5)"},
                "type_filtre": {"type": "string"},
                "mot_cle": {"type": "string"},
                "article_id": {"type": "string"},
                "source": {"type": "string"},
                "date_debut": {"type": "string", "description": "YYYY-MM-DD"},
                "date_fin": {"type": "string", "description": "YYYY-MM-DD"},
            },
        },
    }},
    {"type": "function", "function": {
        "name": "compter_articles",
        "description": "Compte le nombre total d'articles correspondant à des filtres (ou tous si aucun filtre).",
        "parameters": {
            "type": "object",
            "properties": {
                "type_filtre": {"type": "string"},
                "mot_cle": {"type": "string"},
                "source": {"type": "string"},
                "date_debut": {"type": "string"},
                "date_fin": {"type": "string"},
            },
        },
    }},
    {"type": "function", "function": {
        "name": "ajouter_article",
        "description": "Ajoute un nouvel article dans la base.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "type": {"type": "string"},
                "titre": {"type": "string"},
                "link": {"type": "string"},
                "date_publication": {"type": "string"},
                "resume": {"type": "string"},
            },
            "required": ["source", "type", "titre"],
        },
    }},
    {"type": "function", "function": {
        "name": "modifier_article",
        "description": "Modifie un ou plusieurs champs d'un article existant, identifié par son ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "article_id": {"type": "string"},
                "champs": {
                    "type": "object",
                    "description": "Dictionnaire des colonnes à modifier, ex: {\"titre\": \"nouveau titre\"}",
                },
            },
            "required": ["article_id", "champs"],
        },
    }},
    {"type": "function", "function": {
        "name": "lire_contenu_lien",
        "description": (
            "Récupère et lit le contenu texte de la page web d'un article à partir de son lien (URL). "
            "Utile quand l'utilisateur demande de lire, résumer en détail, ou analyser le contenu "
            "complet d'un article au-delà du simple résumé stocké en base."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "L'URL du lien à consulter (champ 'link' de l'article)"},
            },
            "required": ["url"],
        },
    }},
    {"type": "function", "function": {
        "name": "supprimer_article",
        "description": (
            "Supprime définitivement un article par son ID. "
            "NE JAMAIS appeler cet outil sans que l'utilisateur ait explicitement "
            "confirmé la suppression dans son dernier message (mot 'confirme' ou équivalent clair)."
        ),
        "parameters": {
            "type": "object",
            "properties": {"article_id": {"type": "string"}},
            "required": ["article_id"],
        },
    }},
]

PROMPT_SYSTEME = """Tu es un assistant qui aide à consulter et gérer une base d'articles de veille économique.
Utilise les outils disponibles pour répondre aux demandes de l'utilisateur.

Règles impératives :
- Pour "modifier_article" ou "supprimer_article" : si l'utilisateur n'a pas clairement
  et explicitement confirmé l'action (ex: il a dit "oui, confirme", "vas-y, supprime-le"),
  NE PAS appeler l'outil. À la place, décris précisément l'action envisagée et demande
  une confirmation explicite.
- Ne jamais inventer un article_id : demande-le si tu ne l'as pas.
- Si l'utilisateur veut lire le contenu complet d'un article (pas juste le résumé),
  récupère d'abord l'article via "rechercher_articles" pour obtenir son "link",
  puis appelle "lire_contenu_lien" avec cette URL. Si la lecture échoue (site
  inaccessible, erreur), dis-le clairement à l'utilisateur au lieu d'inventer un contenu.
- Réponds toujours en français, de façon claire et concise.
"""


class ChatbotArticles:
    def __init__(self, model="llama-3.3-70b-versatile"):
        cle_api = os.getenv("GROQ_API_KEY")
        if not cle_api:
            raise ValueError("GROQ_API_KEY introuvable : vérifie ton fichier .env")

        self.client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=cle_api)
        self.model = model
        self.db = Database()
        self.historique = [{"role": "system", "content": PROMPT_SYSTEME}]

    def _executer_outil(self, nom, arguments):
        try:
            if nom == "rechercher_articles":
                resultats = self.db.get_articles(**arguments)
                return json.dumps(resultats, default=str, ensure_ascii=False)

            if nom == "compter_articles":
                total = self.db.compter_articles(**arguments)
                return json.dumps({"total": total})

            if nom == "ajouter_article":
                nouvel_id = self.db.ajouter_article(**arguments)
                return json.dumps({"succes": True, "id": nouvel_id})

            if nom == "modifier_article":
                n = self.db.modifier_article(arguments["article_id"], arguments["champs"])
                return json.dumps({"succes": n > 0, "lignes_modifiees": n})

            if nom == "lire_contenu_lien":
                contenu = lire_page_web(arguments.get("url", ""))
                return json.dumps({"contenu": contenu})

            if nom == "supprimer_article":
                n = self.db.supprimer_article(arguments["article_id"])
                return json.dumps({"succes": n > 0, "lignes_supprimees": n})

            return json.dumps({"erreur": f"Outil inconnu : {nom}"})
        except Exception as e:
            return json.dumps({"erreur": str(e)})

    def repondre(self, message_utilisateur: str) -> str:
        self.historique.append({"role": "user", "content": message_utilisateur})

        # Boucle tool-calling : le modèle peut enchaîner plusieurs appels d'outils
        for _ in range(5):
            reponse = self.client.chat.completions.create(
                model=self.model,
                messages=self.historique,
                tools=OUTILS,
            )
            msg = reponse.choices[0].message

            if not msg.tool_calls:
                self.historique.append({"role": "assistant", "content": msg.content})
                return msg.content

            self.historique.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": msg.tool_calls,
            })

            for appel in msg.tool_calls:
                nom = appel.function.name
                arguments = json.loads(appel.function.arguments or "{}")
                resultat = self._executer_outil(nom, arguments)
                self.historique.append({
                    "role": "tool",
                    "tool_call_id": appel.id,
                    "content": resultat,
                })

        return "Désolé, je n'ai pas réussi à traiter la demande."

    def fermer(self):
        self.db.fermer()


if __name__ == "__main__":
    bot = ChatbotArticles()
    print("Chatbot articles (tape 'quit' pour arrêter)\n")

    while True:
        message = input("Toi : ").strip()
        if message.lower() in ("quit", "exit"):
            break
        print("\nBot :", bot.repondre(message), "\n")

    bot.fermer()
    print("Au revoir !")