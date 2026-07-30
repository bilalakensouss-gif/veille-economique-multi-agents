"""
orchestrator.py
================
MASOrchestrator : le chef d'orchestre du système multi-agents.

Modèle suivi (validé par l'encadrant) : chaque article est CATÉGORISÉ
puis affecté à UN SEUL agent correspondant (MarketAgent, RiskAgent ou
SupplierAgent) — pas aux trois. Le résultat de cet agent unique est
ensuite transmis à AlertAgent pour décider d'une alerte.

Rôle de l'orchestrateur :
- récupère les articles à traiter (via db.py)
- télécharge et nettoie le contenu de chaque article
- identifie la catégorie de l'article (risque / marché / fournisseur)
- envoie l'article à l'agent correspondant à cette catégorie
- transmet le résultat de cet agent à AlertAgent
- isole les erreurs : un article ou un agent en échec ne bloque jamais
  le reste du cycle
- construit le document JSON final du cycle

Ce que l'orchestrateur NE fait PAS : il n'analyse jamais lui-même
le contenu d'un article (le marché, le risque ou le fournisseur).
La catégorisation est une décision de ROUTAGE, pas une analyse
métier — c'est un simple aiguillage vers le bon spécialiste.
"""

import re
import requests
from datetime import datetime, timezone

import db
from agents.base_agent import BaseAgent
from agents.risk_agent import RiskAgent
from agents.market_agent import MarketAgent
from agents.supplier_agent import SupplierAgent
from agents.alert_agent import AlertAgent


def _telecharger_et_nettoyer(url: str, longueur_max: int = 6000) -> str:
    """
    Télécharge une page web et en extrait le texte principal,
    en supprimant scripts, styles et balises HTML.

    Retourne une chaîne vide en cas d'échec (l'appelant doit vérifier).
    """
    if not url or not url.startswith(("http://", "https://")):
        return ""

    en_tetes = {"User-Agent": "Mozilla/5.0 (compatible; VeilleBot/1.0)"}
    try:
        reponse = requests.get(url, headers=en_tetes, timeout=8)
        reponse.raise_for_status()
    except requests.exceptions.RequestException:
        return ""

    html = reponse.text
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    texte = re.sub(r"<[^>]+>", "\n", html)
    texte = (texte.replace("&nbsp;", " ").replace("&amp;", "&")
                  .replace("&lt;", "<").replace("&gt;", ">")
                  .replace("&quot;", '"').replace("&#39;", "'"))

    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    texte_propre = "\n".join(lignes)

    if len(texte_propre) > longueur_max:
        texte_propre = texte_propre[:longueur_max] + "\n[... contenu tronqué ...]"

    return texte_propre


class MASOrchestrator:

    CATEGORIES_VALIDES = {"risque", "marche", "fournisseur"}

    def __init__(self):
        # Un agent générique, léger, dédié UNIQUEMENT au routage (catégorisation).
        # Ce n'est pas un agent d'analyse métier : il ne fait que déterminer
        # vers quel spécialiste envoyer l'article.
        self._categoriseur = BaseAgent()

        # Les agents spécialisés, un seul étant appelé par article selon la catégorie
        self._agents_par_categorie = {
            "risque": RiskAgent(),
            "marche": MarketAgent(),
            "fournisseur": SupplierAgent(),
        }
        self.alert_agent = AlertAgent()

    def _identifier_categorie(self, titre: str, contenu: str) -> dict:
        """
        Détermine la catégorie de l'article : "risque", "marche" ou
        "fournisseur". Ceci est un simple ROUTAGE, pas une analyse
        métier (l'orchestrateur ne juge jamais le fond du risque, de
        la tendance ou du fournisseur lui-même).
        """
        prompt = f"""
        Tu dois uniquement CATÉGORISER cet article, sans l'analyser en détail.

        Titre : {titre}
        Contenu (extrait) : {contenu[:1500]}

        Choisis UNE seule catégorie parmi :
        - "risque" : l'article parle principalement d'un risque (cyber,
          réglementaire, financier, réputationnel...)
        - "marche" : l'article parle principalement d'une tendance de
          marché, économique ou technologique
        - "fournisseur" : l'article parle principalement d'un fournisseur
          (mention, incident, changement de statut...)

        Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
        {{"categorie": "risque" | "marche" | "fournisseur"}}
        """
        return self._categoriseur.call_model(prompt)

    def lancer_cycle(self, depuis_date=None, limite: int = 50, ids_a_reessayer=None) -> dict:
        """
        Lance un cycle complet et retourne le document JSON final
        (statistiques, résultats, alertes, erreurs).

        `ids_a_reessayer` : IDs d'articles ayant échoué lors d'un cycle
        précédent, à traiter à nouveau même s'ils sont antérieurs à
        `depuis_date` (sinon ils seraient ignorés pour toujours).
        """
        debut = datetime.now(timezone.utc)
        articles = db.get_articles_a_traiter(depuis_date=depuis_date, limite=limite)

        # Ajout des articles en échec du cycle précédent, sans doublon
        if ids_a_reessayer:
            deja_presents = {a["id"] for a in articles}
            ids_manquants = [i for i in ids_a_reessayer if i not in deja_presents]
            articles += db.get_articles_par_ids(ids_manquants)

        resultats = []
        alertes = []
        nb_erreurs = 0
        nb_analyses = 0
        derniere_date_created_at = None
        ids_en_echec = set()  # articles ayant échoué au moins une fois dans ce cycle

        for article in articles:
            article_id = article["id"]
            titre = article["titre"]
            lien = article["link"]
            created_at = article["created_at"]

            if derniere_date_created_at is None or created_at > derniere_date_created_at:
                derniere_date_created_at = created_at

            # --- Récupération du contenu ---
            contenu = _telecharger_et_nettoyer(lien)
            if not contenu:
                nb_erreurs += 1
                ids_en_echec.add(article_id)
                resultats.append({
                    "agent_name": "orchestrator",
                    "article_id": article_id,
                    "status": "FAILED",
                    "concerned": None,
                    "confidence": None,
                    "result": None,
                    "error_message": f"Impossible de récupérer le contenu depuis le lien : {lien}",
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # --- Catégorisation (routage vers UN SEUL agent) ---
            sortie_categorie = self._identifier_categorie(titre, contenu)
            categorie = sortie_categorie.get("categorie")

            if sortie_categorie.get("status") != "SUCCESS" or categorie not in self.CATEGORIES_VALIDES:
                nb_erreurs += 1
                ids_en_echec.add(article_id)
                resultats.append({
                    "agent_name": "orchestrator",
                    "article_id": article_id,
                    "status": "FAILED",
                    "concerned": None,
                    "confidence": None,
                    "result": None,
                    "error_message": sortie_categorie.get(
                        "error_message", f"Catégorie invalide ou manquante : {categorie}"
                    ),
                    "processed_at": datetime.now(timezone.utc).isoformat(),
                })
                continue

            # --- Analyse par l'agent correspondant (un seul) ---
            agent_choisi = self._agents_par_categorie[categorie]
            nom_agent_choisi = type(agent_choisi).__name__

            sortie_agent = agent_choisi.analyser(texte_article=contenu, titre=titre)
            statut_agent = sortie_agent.get("status", "FAILED")

            resultat_agent = {
                "agent_name": nom_agent_choisi,
                "article_id": article_id,
                "status": statut_agent,
                "concerned": sortie_agent.get("concerned"),
                "confidence": sortie_agent.get("confidence"),
                "result": sortie_agent.get("result"),
                "error_message": sortie_agent.get("error_message"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            resultats.append(resultat_agent)

            if statut_agent != "SUCCESS":
                nb_erreurs += 1
                ids_en_echec.add(article_id)

            # --- Décision d'alerte, basée sur le résultat de CET agent unique ---
            if statut_agent == "SUCCESS":
                sortie_alerte = self.alert_agent.evaluer(
                    article_id=article_id,
                    titre=titre,
                    resultats_agents=[resultat_agent],
                )

                if sortie_alerte.get("status") == "SUCCESS" and sortie_alerte.get("concerned"):
                    alertes.append({
                        "alerte_id": f"ALT-{article_id}",
                        "niveau": sortie_alerte["result"].get("niveau"),
                        "titre": sortie_alerte["result"].get("titre_alerte"),
                        "article_id": article_id,
                        "agent_source": "AlertAgent",
                        "description": sortie_alerte["result"].get("description"),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                elif sortie_alerte.get("status") != "SUCCESS":
                    nb_erreurs += 1
                    ids_en_echec.add(article_id)

            nb_analyses += 1

        fin = datetime.now(timezone.utc)
        statut_global = "SUCCESS" if nb_erreurs == 0 else "SUCCESS_WITH_WARNINGS"

        return {
            "cycle_started_at": debut.isoformat(),
            "cycle_finished_at": fin.isoformat(),
            "status": statut_global,
            "articles_recus": len(articles),
            "articles_analyses": nb_analyses,
            "erreurs": nb_erreurs,
            "alertes_creees": len(alertes),
            "resultats": resultats,
            "alertes": alertes,
            "derniere_date_created_at": derniere_date_created_at.isoformat() if derniere_date_created_at else None,
            "articles_en_echec": sorted(ids_en_echec),
        }