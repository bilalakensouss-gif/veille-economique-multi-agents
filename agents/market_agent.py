from agents.base_agent import BaseAgent


class MarketAgent(BaseAgent):

    def analyser(self, texte_article: str, titre: str = "") -> dict:
        
        prompt = f"""
        Tu es un analyste de tendances de marché et économiques.

        Titre de l'article : {titre}
        Contenu de l'article :
        {texte_article}

        Détermine si cet article révèle une tendance de marché pertinente
        (technologique, économique, sectorielle, réglementaire favorable
        ou défavorable à un secteur, etc.).

        Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
        {{
          "concerned": true ou false,
          "confidence": nombre entre 0 et 1,
          "result": {{
            "secteur": "nom du secteur concerné",
            "tendance": "hausse|baisse|stable",
            "impact": "faible|moyen|eleve",
            "justification": "courte explication de l'évaluation"
          }}
        }}
        """
        return self.call_model(prompt)


