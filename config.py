import os
from dotenv import load_dotenv
load_dotenv()  


def _valeur_obligatoire(nom_variable: str) -> str:
  
    valeur = os.getenv(nom_variable)
    if not valeur:
        raise ValueError(
            f"Variable manquante dans le .env : {nom_variable}. "
            f"Vérifie que ton fichier .env est au bon endroit et contient cette clé."
        )
    return valeur



OPENROUTER_API_KEY = _valeur_obligatoire("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")  


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = _valeur_obligatoire("DB_NAME")
DB_USER = _valeur_obligatoire("DB_USER")
DB_PASSWORD = _valeur_obligatoire("DB_PASSWORD")


TABLE_ARTICLES = os.getenv("TABLE_ARTICLES", "economic_watch_article")


if __name__ == "__main__":
  
    print("Configuration chargée avec succès :")
    print(f"  OPENROUTER_MODEL = {OPENROUTER_MODEL}")
    print(f"  DB_HOST    = {DB_HOST}")
    print(f"  DB_PORT    = {DB_PORT}")
    print(f"  DB_NAME    = {DB_NAME}")
    print(f"  DB_USER    = {DB_USER}")
    print(f"  TABLE_ARTICLES = {TABLE_ARTICLES}")
    print(f"  OPENROUTER_API_KEY présente : {'oui' if OPENROUTER_API_KEY else 'non'}")
    print(f"  DB_PASSWORD présent   : {'oui' if DB_PASSWORD else 'non'}")