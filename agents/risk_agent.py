from agents.base_agent import BaseAgent


class RiskAgent(BaseAgent):

    def analyser(self, texte_article: str, titre: str = "") -> dict:
        """
        Analyse un article et détermine s'il représente un risque,
        avec un score de confiance et une analyse structurée.
        """
        prompt = f"""
        Tu es un analyste de risques économiques, cybersécurité et réglementaires.

        Titre de l'article : {titre}
        Contenu de l'article :
        {texte_article}

        Détermine si cet article concerne un risque (cyber, réglementaire,
        financier, réputationnel, etc.) pour une entreprise ou une institution.

        Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
        {{
          "concerned": true ou false,
          "confidence": nombre entre 0 et 1,
          "result": {{
            "type_risque": "cyber|reglementaire|financier|reputationnel|autre|aucun",
            "criticite": "faible|moyen|critique",
            "score_risque": nombre entre 0 et 10,
            "entite_concernee": "nom de l'entité concernée si identifiable, sinon null",
            "justification": "courte explication de l'évaluation"
          }}
        }}
        """
        return self.call_model(prompt)


