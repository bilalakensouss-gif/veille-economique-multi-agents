"""
agents/market_agent.py
========================
Agent spécialisé : identifie les tendances de marché (technologiques,
économiques, sectorielles) dans le texte d'un article.

Même principe que RiskAgent : reçoit un texte, retourne du JSON structuré,
ne connaît ni la base de données, ni les autres agents.
"""

from agents.base_agent import BaseAgent


class MarketAgent(BaseAgent):

    def analyser(self, texte_article: str, titre: str = "") -> dict:
        """
        Analyse un article et détermine s'il révèle une tendance de marché
        pertinente, avec un score de confiance et une analyse structurée.
        """
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


