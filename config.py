"""
config.py
=========
Lecture centralisée de toutes les variables de configuration
(clés API LLM + connexion PostgreSQL) depuis le fichier .env.

Aucun autre fichier du projet ne doit appeler os.getenv() directement :
tout passe par ce module, pour avoir un seul endroit à modifier
si un nom de variable change.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # charge les variables du fichier .env dans l'environnement


def _valeur_obligatoire(nom_variable: str) -> str:
    """Récupère une variable d'environnement, ou lève une erreur claire si absente."""
    valeur = os.getenv(nom_variable)
    if not valeur:
        raise ValueError(
            f"Variable manquante dans le .env : {nom_variable}. "
            f"Vérifie que ton fichier .env est au bon endroit et contient cette clé."
        )
    return valeur


# ---------- Clé API du LLM ----------
GROQ_API_KEY = _valeur_obligatoire("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # valeur par défaut si non précisé

# ---------- Connexion PostgreSQL ----------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = _valeur_obligatoire("DB_NAME")
DB_USER = _valeur_obligatoire("DB_USER")
DB_PASSWORD = _valeur_obligatoire("DB_PASSWORD")

# ---------- Nom de la table des articles ----------
# Rendu configurable pour que le code s'adapte facilement à une autre base
# ou un autre nom de table, sans toucher au code source.
TABLE_ARTICLES = os.getenv("TABLE_ARTICLES", "economic_watch_article")


if __name__ == "__main__":
    # Petit test rapide : lance juste "python config.py" pour vérifier
    # que toutes les variables sont bien lues (sans afficher les secrets en clair).
    print("Configuration chargée avec succès :")
    print(f"  GROQ_MODEL = {GROQ_MODEL}")
    print(f"  DB_HOST    = {DB_HOST}")
    print(f"  DB_PORT    = {DB_PORT}")
    print(f"  DB_NAME    = {DB_NAME}")
    print(f"  DB_USER    = {DB_USER}")
    print(f"  TABLE_ARTICLES = {TABLE_ARTICLES}")
    print(f"  GROQ_API_KEY présente : {'oui' if GROQ_API_KEY else 'non'}")
    print(f"  DB_PASSWORD présent   : {'oui' if DB_PASSWORD else 'non'}")