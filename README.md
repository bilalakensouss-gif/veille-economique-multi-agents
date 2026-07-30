# Veille Économique Multi-Agents

Système multi-agents qui analyse automatiquement des articles de veille économique stockés dans une base PostgreSQL, en s'appuyant sur des agents IA spécialisés (risque, marché, fournisseur) et un orchestrateur central.

Projet réalisé dans le cadre d'un stage chez **CanTek**.

## Sommaire

- [Architecture](#architecture)
- [Fonctionnement d'un cycle](#fonctionnement-dun-cycle)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [API](#api)
- [Structure du projet](#structure-du-projet)
- [Exemple de sortie](#exemple-de-sortie)

## Architecture

```
Base de données (PostgreSQL)
        │
        ▼
  MASOrchestrator
        │
        ├── télécharge et nettoie le contenu de chaque article
        ├── catégorise l'article (risque / marché / fournisseur)
        ├── envoie l'article à l'agent correspondant (un seul)
        │       ├── RiskAgent
        │       ├── MarketAgent
        │       └── SupplierAgent
        └── transmet le résultat à AlertAgent
                └── décide de créer une alerte ou non
```

**Principe clé** : l'orchestrateur ne fait jamais lui-même l'analyse métier (risque, tendance, fournisseur). Il se contente de catégoriser et de router chaque article vers l'agent spécialisé correspondant. Chaque agent hérite d'une classe commune `BaseAgent` qui gère l'appel au modèle LLM, la validation du JSON reçu et les tentatives de réessai (jusqu'à 2 tentatives supplémentaires en cas de réponse invalide).

## Fonctionnement d'un cycle

1. **Sélection des articles** — récupération des articles créés après la dernière date traitée (`created_at`), plus les articles ayant échoué lors d'un cycle précédent (réessayés automatiquement).
2. **Récupération du contenu** — téléchargement de la page via son lien, nettoyage du HTML (suppression des scripts, styles, balises).
3. **Catégorisation** — un appel léger au LLM détermine la catégorie de l'article : `risque`, `marche` ou `fournisseur`.
4. **Analyse** — l'agent correspondant à la catégorie analyse le contenu et retourne un résultat structuré (JSON).
5. **Alerte** — le résultat de l'agent est transmis à `AlertAgent`, qui décide si une alerte doit être créée.
6. **Bilan** — un document JSON récapitule le cycle : statistiques, résultats, alertes créées, erreurs.

Toute erreur (téléchargement, catégorisation, analyse, alerte) est isolée : elle n'interrompt jamais le reste du cycle, et l'article concerné est automatiquement réessayé au cycle suivant.

## Installation

### Prérequis

- Python 3.10+
- Une base PostgreSQL locale déjà peuplée (table configurable via `.env`)
- Une clé API [Groq](https://console.groq.com) (modèle LLM gratuit et rapide)

### Dépendances

```bash
pip install psycopg2-binary openai python-dotenv requests fastapi uvicorn
```

### Configuration

Créer un fichier `.env` à la racine du projet :

```dotenv
GROQ_API_KEY=ta_cle_groq
GROQ_MODEL=llama-3.3-70b-versatile

DB_HOST=localhost
DB_PORT=5432
DB_NAME=market_intelligence
DB_USER=postgres
DB_PASSWORD=ton_mot_de_passe

TABLE_ARTICLES=economic_watch_article
```

Vérifier que la configuration est bien lue :

```bash
python config.py
```

## Utilisation

### Lancer un cycle en ligne de commande

```bash
# Traite les nouveaux articles depuis le dernier cycle
python main.py

# Traite au maximum 10 articles
python main.py --limite 10

# Force une date de départ précise
python main.py --depuis 2026-07-01

# Ignore l'historique, traite les derniers articles sans filtre de date
python main.py --ignorer-historique
```

Chaque exécution :
- affiche un résumé lisible dans le terminal (statut, articles traités, alertes, erreurs)
- sauvegarde le bilan complet dans un fichier `resultat_cycle_<horodatage>.json`
- met à jour `derniere_date_traitee.txt`, qui retient la date de curseur et les articles en échec à réessayer

### Idempotence

Le fichier `derniere_date_traitee.txt` garantit qu'un article n'est jamais analysé deux fois, sauf s'il a échoué lors d'un cycle précédent — auquel cas il est automatiquement repris au cycle suivant.

## API

Une API minimale expose le déclenchement d'un cycle via une requête HTTP.

```bash
uvicorn api:app --reload
```

Puis :

```bash
curl -X POST http://localhost:8000/cycle/start
```

Ou via l'interface interactive : [http://localhost:8000/docs](http://localhost:8000/docs)

L'appel est **synchrone** : il attend la fin complète du cycle avant de retourner le bilan JSON dans la même réponse.

## Structure du projet

```
veille_economique/
├── .env
├── config.py                 # lecture centralisée des variables d'environnement
├── db.py                      # connexion PostgreSQL, lecture des articles
├── orchestrator.py            # MASOrchestrator : coordination du cycle
├── main.py                    # point d'entrée en ligne de commande
├── api.py                     # API HTTP (FastAPI)
│
└── agents/
    ├── base_agent.py           # classe commune : appel LLM, validation JSON, retry
    ├── risk_agent.py            # détection de risques
    ├── market_agent.py          # tendances de marché
    ├── supplier_agent.py        # informations fournisseurs
    └── alert_agent.py            # création d'alertes à partir des résultats
```

## Exemple de sortie

```json
{
  "cycle_started_at": "2026-07-30T18:38:06.635122+00:00",
  "cycle_finished_at": "2026-07-30T18:38:50.031255+00:00",
  "status": "SUCCESS",
  "articles_recus": 3,
  "articles_analyses": 3,
  "erreurs": 0,
  "alertes_creees": 3,
  "resultats": [
    {
      "agent_name": "RiskAgent",
      "article_id": "b4a8c21abb",
      "status": "SUCCESS",
      "concerned": true,
      "confidence": 0.9,
      "result": {
        "type_risque": "reglementaire",
        "criticite": "moyen",
        "score_risque": 6,
        "entite_concernee": "Investisseurs et entreprises de marché",
        "justification": "..."
      },
      "error_message": null,
      "processed_at": "2026-07-30T18:38:17.057048+00:00"
    }
  ],
  "alertes": [
    {
      "alerte_id": "ALT-b4a8c21abb",
      "niveau": "moyen",
      "titre": "Risque d'investissement non autorisé",
      "article_id": "b4a8c21abb",
      "agent_source": "AlertAgent",
      "description": "...",
      "created_at": "2026-07-30T18:38:18.391616+00:00"
    }
  ],
  "derniere_date_created_at": "2026-07-30T18:38:06.635122+00:00",
  "articles_en_echec": []
}
```

## Périmètre

**Inclus** : orchestrateur, agents spécialisés, catégorisation automatique, gestion d'erreurs et retry, idempotence, API de déclenchement.

**Hors périmètre** (volontairement, selon le cahier des charges) : RAG, embeddings, recherche vectorielle, chatbot conversationnel, écriture des résultats en base (à intégrer ultérieurement), décisions métier sans validation humaine.