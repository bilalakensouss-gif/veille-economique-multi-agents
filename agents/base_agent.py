import json
from openai import OpenAI
import config


class BaseAgent:

    def __init__(self, model: str = None):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=config.GROQ_API_KEY,
        )
        self.model = model or config.GROQ_MODEL

    def call_model(self, prompt: str, tentatives_max: int = 3) -> dict:
        derniere_erreur = None

        for tentative in range(1, tentatives_max + 1):
            try:
                reponse = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                texte = reponse.choices[0].message.content.strip()
                texte = texte.replace("```json", "").replace("```", "").strip()

                resultat = json.loads(texte)
                resultat["status"] = "SUCCESS"
                return resultat

            except json.JSONDecodeError as e:
                derniere_erreur = f"Réponse non-JSON du modèle (tentative {tentative}) : {e}"

            except Exception as e:
                derniere_erreur = f"Erreur d'appel au modèle (tentative {tentative}) : {e}"
        return {"status": "FAILED", "error_message": derniere_erreur}