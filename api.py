"""

API simple exposant un seul endpoint : POST /cycle/start

Ce endpoint est SYNCHRONE : il démarre le cycle, attend qu'il se
termine entièrement, puis retourne directement le bilan JSON complet
dans la même réponse. Pas besoin d'un second appel pour consulter le
résultat.

Pour lancer ce serveur :
    uvicorn api:app --reload
Puis tester en local::
    curl -X POST http://localhost:8000/cycle/start
ou directement depuis un navigateur/Postman.:  http://localhost:8000/docs
"""

from fastapi import FastAPI
from main import executer_cycle, lire_etat

app = FastAPI(title="API Veille Économique Multi-Agents")


@app.post("/cycle/start")
def demarrer_cycle(limite: int = 50):
  
    depuis_date, ids_a_reessayer = lire_etat()

    bilan = executer_cycle(
        depuis_date=depuis_date,
        limite=limite,
        ids_a_reessayer=ids_a_reessayer,
    )

    return bilan


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)