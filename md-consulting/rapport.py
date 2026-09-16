"""Rapport en quatre blocs, identiques pour tous les publics.
Seuls les intitulés et les pistes proposées changent selon le public.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import dates_fr
import db
import personne as P
import questionnaire as Q
import ressources as Rs
import resultat_test as RT
import seance as S

# Les quatre blocs, dans l'ordre. Les intitulés du 4e bloc changent de nom
# selon le public : le gabarit reste le même, la question posée diffère.
BLOCS = ("bloc_situation", "bloc_tests_utilises", "bloc_resultats", "bloc_solutions")

INTITULES_COMMUNS = {
    "bloc_situation": "Situation",
    "bloc_tests_utilises": "Outils utilisés",
    "bloc_resultats": "Ce qui ressort",
}

INTITULES_SOLUTIONS = {
    "college": "Pistes et prochaines étapes",
    "lycee": "Pistes d'orientation et démarches à engager",
    "reconversion": "Pistes professionnelles et démarches à engager",
    "vae": "Démarches VAE à engager",
    "handicap": "Pistes et appuis mobilisables",
    "burnout": "Appuis mobilisables et prochaines étapes, à rythme tenable",
}


def intitules(public: str) -> dict[str, str]:
    return {**INTITULES_COMMUNS,
            "bloc_solutions": INTITULES_SOLUTIONS.get(public, "Pistes et démarches")}


@dataclass
class Rapport:
    seance_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date_generation: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    bloc_situation: str = ""
    bloc_tests_utilises: str = ""
    bloc_resultats: str = ""
    bloc_solutions: str = ""
    export_docx_path: str | None = None

    @property
    def blocs_vides(self) -> list[str]:
        return [b for b in BLOCS if not getattr(self, b).strip()]

    def valider(self) -> None:
        if not self.seance_id:
            raise ValueError("Un rapport doit être rattaché à une séance.")


def resume_tests(seance_id: str, chemin: Path | str | None = None) -> str:
    """Bloc « outils utilisés » : liste factuelle, rédigée depuis la base.
    C'est le seul bloc que l'outil remplit seul — les trois autres relèvent
    du consultant, pas d'une génération automatique."""
    resultats = RT.lister_par_seance(seance_id, chemin)
    if not resultats:
        return "Aucun outil enregistré pour cette séance."
    lignes = []
    for r in resultats:
        lignes.append(f"{RT.libelle(r.type_test)} — "
                      f"{dates_fr.jour(r.date_saisie)}")
    return "\n".join(lignes)


def composer_situation(pers: P.Personne, sea: S.Seance) -> str:
    """Bloc 1, assemblé depuis la fiche et la séance. Que des faits saisis."""
    lignes = [f"Personne reçue : {pers.nom_affiche}"
              + (f", {pers.age} ans" if pers.age is not None else "")
              + f" — {P.PUBLICS[pers.public]}."]
    if pers.rqth:
        lignes.append("Reconnaissance de la qualité de travailleur handicapé (RQTH).")
    if pers.situation:
        lignes.append(f"Situation : {pers.situation}.")
    lignes.append(f"Séance du {dates_fr.jour(sea.date)}, "
                  f"durée prévue {sea.chrono_max_minutes} minutes.")
    if sea.objectif_texte:
        lignes.append(f"Objectif annoncé : {sea.objectif_texte}")
    if pers.notes_libres:
        lignes.append(f"Notes de séance : {pers.notes_libres}")
    return "\n".join(lignes)


def composer_resultats(seance_id: str, chemin: Path | str | None = None) -> str:
    """Bloc 3 : les synthèses des outils passés, mises bout à bout.

    Aucune interprétation ajoutée : ce qui apparaît ici a été produit par les
    grilles des outils eux-mêmes. Les outils marqués « donnée de santé » n'y
    figurent pas — rien n'en a été enregistré, il n'y a rien à reprendre.
    """
    resultats = RT.lister_par_seance(seance_id, chemin)
    if not resultats:
        return ""
    blocs = []
    for r in resultats:
        if not (r.synthese_texte or "").strip():
            continue
        blocs.append(f"{RT.libelle(r.type_test)}\n{r.synthese_texte.strip()}")
    return "\n\n".join(blocs)


def composer_solutions(pers: P.Personne, seance_id: str,
                       chemin: Path | str | None = None) -> str:
    """Bloc 4 : démarches issues des outils passés, puis ressources du public.

    Rien n'est inventé : les démarches sont celles que les outils prévoient
    eux-mêmes après la passation, et les ressources sont celles du catalogue,
    avec leur statut d'accès.
    """
    lignes = []
    installes = Q.disponibles()
    passes = [r.type_test for r in RT.lister_par_seance(seance_id, chemin)]
    suites = []
    for cle in dict.fromkeys(passes):
        q = installes.get(cle)
        for etape in (q.get("suite", []) if q else []):
            if etape not in suites:
                suites.append(etape)
    if suites:
        lignes.append("À faire à la suite des outils passés :")
        lignes += [f"- {e}" for e in suites]
        lignes.append("")

    ressources = Rs.pour_public(pers.public)
    if ressources:
        lignes.append("Ressources à consulter :")
        for r in ressources:
            mention = f"- {r.nom} — {r.url} ({r.acces})"
            lignes.append(mention)
    # Le texte repris ici s'adresse à la personne reçue, pas au consultant :
    # la mise en garde professionnelle reste à l'écran, hors du document.
    orientation = Rs.ORIENTATIONS_BENEFICIAIRE.get(pers.public)
    if orientation:
        lignes += ["", orientation]
    return "\n".join(lignes)


def composer(pers: P.Personne, sea: S.Seance,
             chemin: Path | str | None = None) -> dict[str, str]:
    """Les quatre blocs, assemblés depuis la base. Tous modifiables ensuite."""
    return {
        "bloc_situation": composer_situation(pers, sea),
        "bloc_tests_utilises": resume_tests(sea.id, chemin),
        "bloc_resultats": composer_resultats(sea.id, chemin),
        "bloc_solutions": composer_solutions(pers, sea.id, chemin),
    }


def preparer(seance_id: str, chemin: Path | str | None = None) -> Rapport:
    """Compte rendu assemblé automatiquement, prêt à être relu et corrigé."""
    sea = S.lire(seance_id, chemin)
    if sea is None:
        raise ValueError("Séance introuvable.")
    pers = P.lire(sea.personne_id, chemin)
    if pers is None:
        raise ValueError("Personne introuvable.")
    return Rapport(seance_id=seance_id, **composer(pers, sea, chemin))


def regenerer(rap: Rapport, chemin: Path | str | None = None) -> Rapport:
    """Réécrit les quatre blocs depuis la base, en écrasant les retouches."""
    sea = S.lire(rap.seance_id, chemin)
    pers = P.lire(sea.personne_id, chemin)
    for cle, texte in composer(pers, sea, chemin).items():
        setattr(rap, cle, texte)
    return rap


_COLONNES = ("id, seance_id, date_generation, bloc_situation, bloc_tests_utilises, "
             "bloc_resultats, bloc_solutions, export_docx_path")


def enregistrer(r: Rapport, chemin: Path | str | None = None) -> Rapport:
    """Insère ou remplace. Un seul compte rendu par séance : la contrainte
    d'unicité fait que le précédent est écarté, quel que soit son identifiant."""
    r.valider()
    with db.connexion(chemin) as cx:
        if not cx.execute("SELECT 1 FROM seance WHERE id = ?", (r.seance_id,)).fetchone():
            raise ValueError("Séance introuvable : rapport non enregistré.")
        cx.execute(f"INSERT OR REPLACE INTO rapport ({_COLONNES}) VALUES (?,?,?,?,?,?,?,?)",
                   (r.id, r.seance_id, r.date_generation, r.bloc_situation,
                    r.bloc_tests_utilises, r.bloc_resultats, r.bloc_solutions,
                    r.export_docx_path))
    return r


def lire_par_seance(seance_id: str, chemin: Path | str | None = None) -> Rapport | None:
    with db.connexion(chemin) as cx:
        l = cx.execute(f"SELECT {_COLONNES} FROM rapport WHERE seance_id = ?",
                       (seance_id,)).fetchone()
    if not l:
        return None
    return Rapport(id=l["id"], seance_id=l["seance_id"],
                   date_generation=l["date_generation"],
                   bloc_situation=l["bloc_situation"] or "",
                   bloc_tests_utilises=l["bloc_tests_utilises"] or "",
                   bloc_resultats=l["bloc_resultats"] or "",
                   bloc_solutions=l["bloc_solutions"] or "",
                   export_docx_path=l["export_docx_path"])
