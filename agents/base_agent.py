"""
agents/base_agent.py
=====================
Classe commune héritée par tous les agents spécialisés (RiskAgent,
MarketAgent, AlertAgent...).

Rôle unique de cette classe : parler au LLM proprement.
- Elle ne connaît PAS les autres agents.
- Elle ne connaît PAS l'orchestrateur.
- Elle ne télécharge et ne nettoie aucun contenu.

Elle gère :
- l'appel au modèle (via Groq, compatible API OpenAI)
- la validation du JSON reçu
- le retry (jusqu'à 2 tentatives supplémentaires) en cas de réponse invalide
"""

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
        """
        Appelle le LLM avec le prompt donné et retourne un dict JSON validé.

        En cas de réponse non-JSON, réessaie jusqu'à `tentatives_max` fois
        au total (donc 2 tentatives supplémentaires après le premier échec,
        comme demandé dans le cahier des charges).

        Retourne toujours un dict avec une clé "status" :
        - "SUCCESS" si le JSON a été obtenu et parsé correctement
        - "FAILED" avec une clé "error_message" sinon
        """
        derniere_erreur = None

        for tentative in range(1, tentatives_max + 1):
            try:
                reponse = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                texte = reponse.choices[0].message.content.strip()

                # certains modèles entourent parfois le JSON de ```json ... ```
                texte = texte.replace("```json", "").replace("```", "").strip()

                resultat = json.loads(texte)
                resultat["status"] = "SUCCESS"
                return resultat

            except json.JSONDecodeError as e:
                derniere_erreur = f"Réponse non-JSON du modèle (tentative {tentative}) : {e}"

            except Exception as e:
                derniere_erreur = f"Erreur d'appel au modèle (tentative {tentative}) : {e}"

        # Toutes les tentatives ont échoué
        return {"status": "FAILED", "error_message": derniere_erreur}