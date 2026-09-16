"""Résultats scolaires et affinités.

Le croisement de la note et de l'affinité dit plus que chacune seule : une
matière aimée et réussie est un appui, une matière aimée mais ratée demande
un travail, une matière réussie sans plaisir n'est pas une piste. C'est de
l'arithmétique, pas une interprétation : le seuil est explicite et affiché.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import db

AIME, NEUTRE, REJET = "aime", "neutre", "n'aime pas"
AFFINITES = (AIME, NEUTRE, REJET)

# Seuil de réussite, sur 20. Choisi ici et non ailleurs pour qu'il soit
# discutable : c'est une convention, pas une vérité.
SEUIL_REUSSITE = 12.0

# Les quatre cases du croisement, avec ce qu'elles veulent dire.
APPUI = "appui : aimée et réussie"
A_TRAVAILLER = "envie sans résultat : à travailler"
SANS_ENVIE = "résultat sans envie : n'en faire ni un projet ni un renoncement"
FRAGILITE = "fragilité : ni résultat ni envie"
SANS_NOTE = "affinité connue, moyenne non communiquée"


@dataclass
class Matiere:
    personne_id: str
    nom: str
    affinite: str = NEUTRE
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    moyenne: float | None = None
    appreciation: str | None = None
    ordre: int = 0

    @property
    def reussie(self) -> bool | None:
        return None if self.moyenne is None else self.moyenne >= SEUIL_REUSSITE

    @property
    def lecture(self) -> str:
        """La case du croisement où tombe cette matière."""
        if self.moyenne is None:
            return SANS_NOTE
        if self.affinite == AIME:
            return APPUI if self.reussie else A_TRAVAILLER
        if self.affinite == REJET:
            return SANS_ENVIE if self.reussie else FRAGILITE
        return "résultat " + ("au-dessus" if self.reussie else "en dessous") + \
               f" du seuil ({SEUIL_REUSSITE:g}/20), affinité neutre"

    def valider(self) -> None:
        if not (self.nom or "").strip():
            raise ValueError("Le nom de la matière est obligatoire.")
        if self.affinite not in AFFINITES:
            raise ValueError(f"Affinité inconnue : {self.affinite!r}")
        if self.moyenne is not None and not 0 <= self.moyenne <= 20:
            raise ValueError("La moyenne doit être comprise entre 0 et 20.")


_CHAMPS = ("id", "personne_id", "nom", "moyenne", "affinite", "appreciation", "ordre")


def _depuis_ligne(l) -> Matiere:
    return Matiere(**{c: l[c] for c in _CHAMPS})


def creer(m: Matiere, chemin: Path | str | None = None) -> Matiere:
    m.valider()
    with db.connexion(chemin) as cx:
        if not cx.execute("SELECT 1 FROM personne WHERE id = ?",
                          (m.personne_id,)).fetchone():
            raise ValueError("Personne introuvable : matière non enregistrée.")
        cx.execute(f"INSERT INTO matiere ({', '.join(_CHAMPS)}) VALUES (?,?,?,?,?,?,?)",
                   tuple(getattr(m, c) for c in _CHAMPS))
    return m


def lister(personne_id: str, chemin: Path | str | None = None) -> list[Matiere]:
    with db.connexion(chemin) as cx:
        return [_depuis_ligne(l) for l in cx.execute(
            f"SELECT {', '.join(_CHAMPS)} FROM matiere WHERE personne_id = ? "
            "ORDER BY ordre, nom COLLATE NOCASE", (personne_id,))]


def remplacer_tout(personne_id: str, matieres: list[Matiere],
                   chemin: Path | str | None = None) -> None:
    """Enregistre la liste telle qu'elle est saisie, d'un bloc."""
    for m in matieres:
        m.valider()
    with db.connexion(chemin) as cx:
        cx.execute("DELETE FROM matiere WHERE personne_id = ?", (personne_id,))
        for i, m in enumerate(matieres):
            m.ordre = i
            cx.execute(f"INSERT INTO matiere ({', '.join(_CHAMPS)}) "
                       "VALUES (?,?,?,?,?,?,?)",
                       tuple(getattr(m, c) for c in _CHAMPS))


def supprimer(matiere_id: str, chemin: Path | str | None = None) -> bool:
    with db.connexion(chemin) as cx:
        c = cx.execute("DELETE FROM matiere WHERE id = ?", (matiere_id,))
    return c.rowcount > 0


def par_lecture(personne_id: str, chemin: Path | str | None = None) -> dict[str, list[Matiere]]:
    """Les matières rangées par case du croisement, dans un ordre utile."""
    groupes: dict[str, list[Matiere]] = {}
    for m in lister(personne_id, chemin):
        groupes.setdefault(m.lecture, []).append(m)
    return groupes


def moyenne_generale(personne_id: str, chemin: Path | str | None = None) -> float | None:
    notes = [m.moyenne for m in lister(personne_id, chemin) if m.moyenne is not None]
    return round(sum(notes) / len(notes), 2) if notes else None
