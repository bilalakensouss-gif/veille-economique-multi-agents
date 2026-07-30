"""
db.py
=====
Connexion à PostgreSQL et lecture des articles à traiter
depuis la table configurée (economic_watch_article par défaut).

Sélection basée uniquement sur created_at : on récupère les articles
créés après la dernière date de traitement connue (depuis_date).
"""

import psycopg2
import config


def get_connexion():
    """Ouvre une nouvelle connexion PostgreSQL à partir de la config centralisée."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def get_articles_a_traiter(depuis_date=None, limite: int = 50) -> list:
    """
    Récupère les articles à analyser : uniquement ceux créés (created_at)
    après `depuis_date`.

    Si `depuis_date` est None, retourne les `limite` articles les plus
    récents (utile pour un premier test, en attendant une vraie table
    de suivi des cycles côté encadrant).
    """
    conn = get_connexion()
    try:
        with conn.cursor() as cur:
            if depuis_date:
                cur.execute(f"""
                    SELECT id, link, titre, resume, date_scraping, created_at
                    FROM {config.TABLE_ARTICLES}
                    WHERE created_at > %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (depuis_date, limite))
            else:
                cur.execute(f"""
                    SELECT id, link, titre, resume, date_scraping, created_at
                    FROM {config.TABLE_ARTICLES}
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (limite,))

            colonnes = ["id", "link", "titre", "resume", "date_scraping", "created_at"]
            return [dict(zip(colonnes, ligne)) for ligne in cur.fetchall()]
    finally:
        conn.close()


def get_articles_par_ids(ids: list) -> list:
    """
    Récupère des articles précis par leurs IDs (utilisé pour réessayer
    les articles en échec lors d'un cycle précédent).
    """
    if not ids:
        return []

    conn = get_connexion()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, link, titre, resume, date_scraping, created_at
                FROM {config.TABLE_ARTICLES}
                WHERE id = ANY(%s);
            """, (ids,))
            colonnes = ["id", "link", "titre", "resume", "date_scraping", "created_at"]
            return [dict(zip(colonnes, ligne)) for ligne in cur.fetchall()]
    finally:
        conn.close()