from agents.base_agent import BaseAgent


class SupplierAgent(BaseAgent):

    def analyser(self, texte_article: str, titre: str = "") -> dict:
        """
        Analyse un article et détermine s'il concerne un fournisseur
        à surveiller, avec un score de confiance et une analyse structurée.
        """
        prompt = f"""
        Tu es un analyste spécialisé dans le suivi des fournisseurs.

        Titre de l'article : {titre}
        Contenu de l'article :
        {texte_article}

        Détermine si cet article concerne un fournisseur (mention d'une
        entreprise fournisseur, incident, changement de statut, difficulté
        financière, rupture d'approvisionnement, etc.) qui mériterait
        d'être surveillé.

        Réponds UNIQUEMENT en JSON, sans texte autour, avec ce format exact :
        {{
          "concerned": true ou false,
          "confidence": nombre entre 0 et 1,
          "result": {{
            "nom_fournisseur": "nom de l'entreprise concernée si identifiable, sinon null",
            "type_information": "incident|opportunite|changement_statut|autre",
            "a_surveiller": true ou false,
            "justification": "courte explication de l'évaluation"
          }}
        }}
        """
        return self.call_model(prompt)


