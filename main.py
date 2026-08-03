

import json
import argparse
import os
from datetime import datetime
from orchestrator import MASOrchestrator

FICHIER_ETAT = "derniere_date_traitee.txt"


def lire_etat():
   
    if not os.path.exists(FICHIER_ETAT):
        return None, []

    with open(FICHIER_ETAT, "r", encoding="utf-8") as f:
        contenu = f.read().strip()

    if not contenu:
        return None, []


    try:
        etat = json.loads(contenu)
        return etat.get("derniere_date"), etat.get("articles_en_echec", [])
    except json.JSONDecodeError:
        return contenu, []


def ecrire_etat(derniere_date: str, articles_en_echec: list):
    """Enregistre la date de curseur et les IDs en échec, pour le prochain lancement."""
    with open(FICHIER_ETAT, "w", encoding="utf-8") as f:
        json.dump({
            "derniere_date": derniere_date,
            "articles_en_echec": articles_en_echec,
        }, f)


def executer_cycle(depuis_date=None, limite: int = 50, ids_a_reessayer=None):
    """Lance un cycle complet et retourne le bilan JSON."""
    if isinstance(depuis_date, str):
        try:
            depuis_date = datetime.strptime(depuis_date, "%Y-%m-%d")
        except ValueError:
            depuis_date = datetime.fromisoformat(depuis_date)

    orchestrateur = MASOrchestrator()
    bilan = orchestrateur.lancer_cycle(
        depuis_date=depuis_date, limite=limite, ids_a_reessayer=ids_a_reessayer
    )

   
    nouvelle_date = bilan["derniere_date_created_at"] or (
        depuis_date.isoformat() if isinstance(depuis_date, datetime) else depuis_date
    )
    ecrire_etat(nouvelle_date, bilan["articles_en_echec"])

    return bilan


def sauvegarder_bilan(bilan: dict, chemin: str = None) -> str:
  
    if chemin is None:
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        chemin = f"resultat_cycle_{horodatage}.json"

    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(bilan, f, indent=2, ensure_ascii=False)
    return chemin


def afficher_resume(bilan: dict):
    """Affiche un résumé lisible du cycle, sans noyer la sortie dans le JSON complet."""
    print("\n" + "=" * 60)
    print("RÉSUMÉ DU CYCLE")
    print("=" * 60)
    print(f"Statut global      : {bilan['status']}")
    print(f"Démarré à          : {bilan['cycle_started_at']}")
    print(f"Terminé à          : {bilan['cycle_finished_at']}")
    print(f"Articles reçus     : {bilan['articles_recus']}")
    print(f"Articles analysés  : {bilan['articles_analyses']}")
    print(f"Erreurs            : {bilan['erreurs']}")
    print(f"Alertes créées     : {bilan['alertes_creees']}")
    print("=" * 60)

    if bilan["alertes"]:
        print("\nAlertes générées :")
        for alerte in bilan["alertes"]:
            print(f"  - [{alerte['niveau'].upper()}] {alerte['titre']} (article {alerte['article_id']})")

    erreurs = [r for r in bilan["resultats"] if r["status"] == "FAILED"]
    if erreurs:
        print("\nErreurs rencontrées :")
        for e in erreurs:
            print(f"  - [{e['agent_name']}] article {e['article_id']} : {e['error_message']}")

    if bilan.get("articles_en_echec"):
        print(f"\n{len(bilan['articles_en_echec'])} article(s) seront réessayés au prochain cycle : "
              f"{', '.join(bilan['articles_en_echec'])}")


if __name__ == "__main__":
   
    parser = argparse.ArgumentParser(description="Lance un cycle de veille économique multi-agents.")
    parser.add_argument("--limite", type=int, default=50, help="Nombre maximum d'articles à traiter")
    parser.add_argument("--depuis", type=str, default=None,
                         help="Date de départ (YYYY-MM-DD). Si absent, reprend automatiquement "
                              "après le dernier article traité (fichier derniere_date_traitee.txt).")
    parser.add_argument("--ignorer-historique", action="store_true",
                         help="Ignore l'historique et traite les derniers articles sans filtre "
                              "de date (utile pour un premier lancement ou un test).")
    args = parser.parse_args()

  
    if args.ignorer_historique:
        depuis_date, ids_a_reessayer = None, []
    elif args.depuis:
        depuis_date, ids_a_reessayer = args.depuis, []
    else:
        depuis_date, ids_a_reessayer = lire_etat()

    print(f"Lancement du cycle (limite={args.limite}, depuis={depuis_date or 'aucune limite de date'}, "
          f"articles à réessayer={len(ids_a_reessayer)})...")

    bilan = executer_cycle(depuis_date=depuis_date, limite=args.limite, ids_a_reessayer=ids_a_reessayer)

    afficher_resume(bilan)

    chemin_sauvegarde = sauvegarder_bilan(bilan)
    print(f"\nBilan complet sauvegardé dans : {chemin_sauvegarde}")