import json
from agents.base_agent import BaseAgent


class AlertAgent(BaseAgent):

    def evaluer(self, article_id: str, titre: str, resultats_agents: list) -> dict:
        """
        Reçoit les résultats déjà produits par les autres agents pour un
        même article, et décide si une alerte doit être créée.

        `resultats_agents` : liste de dicts, chacun étant le résultat
        d'un agent (ex: sortie de RiskAgent.analyser(), MarketAgent.analyser()).
        """
        resultats_texte = json.dumps(resultats_agents, ensure_ascii=False)

        prompt = f"""
        Tu es un agent de génération d'alertes.

        Article concerné (id: {article_id}) : {titre}

        Voici les résultats déjà produits par d'autres agents d'analyse
        pour cet article :
        {resultats_texte}

        Détermine si ces résultats justifient la création d'une alerte
        prioritaire (ex: risque critique détecté, tendance majeure...).

        Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
        {{
          "concerned": true ou false,
          "confidence": nombre entre 0 et 1,
          "result": {{
            "niveau": "faible|moyen|critique",
            "titre_alerte": "court titre de l'alerte si concerned=true, sinon null",
            "description": "explication courte de la raison de l'alerte"
          }}
        }}
        """
        return self.call_model(prompt)


