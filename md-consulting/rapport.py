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


def preparer(seance_id: str, chemin: Path | str | None = None) -> Rapport:
    """Brouillon : le bloc des outils est pré-rempli, le reste attend le texte."""
    if S.lire(seance_id, chemin) is None:
        raise ValueError("Séance introuvable.")
    return Rapport(seance_id=seance_id,
                   bloc_tests_utilises=resume_tests(seance_id, chemin))


_COLONNES = ("id, seance_id, date_generation, bloc_situation, bloc_tests_utilises, "
             "bloc_resultats, bloc_solutions, export_docx_path")


def enregistrer(r: Rapport, chemin: Path | str | None = None) -> Rapport:
    """Insère ou met à jour — un rapport par séance suffit en pratique."""
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
        l = cx.execute(f"SELECT {_COLONNES} FROM rapport WHERE seance_id = ? "
                       "ORDER BY date_generation DESC", (seance_id,)).fetchone()
    if not l:
        return None
    return Rapport(id=l["id"], seance_id=l["seance_id"],
                   date_generation=l["date_generation"],
                   bloc_situation=l["bloc_situation"] or "",
                   bloc_tests_utilises=l["bloc_tests_utilises"] or "",
                   bloc_resultats=l["bloc_resultats"] or "",
                   bloc_solutions=l["bloc_solutions"] or "",
                   export_docx_path=l["export_docx_path"])
