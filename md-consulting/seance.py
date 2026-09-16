"""Séance : modèle, chronomètre et CRUD. Aucune dépendance Streamlit."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date as _date, datetime, time
from pathlib import Path

import db

DUREE_MAX_DEFAUT = 90          # minutes — plafond annoncé dans le brief
MARGE_VIGILANCE = 10           # minutes : on prévient 10 min avant le plafond

# États du chronomètre
NON_DEMARREE = "non_demarree"
EN_COURS = "en_cours"
VIGILANCE = "vigilance"
DEPASSEMENT = "depassement"


@dataclass
class Seance:
    personne_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: str = field(default_factory=lambda: _date.today().isoformat())
    heure_debut: str | None = None
    chrono_max_minutes: int = DUREE_MAX_DEFAUT
    objectif_texte: str | None = None

    @property
    def debut(self) -> datetime | None:
        """Instant de départ reconstruit depuis la base, pas depuis la session.
        Le chronomètre survit donc à un rechargement de page."""
        if not self.heure_debut:
            return None
        try:
            h = time.fromisoformat(self.heure_debut)
            return datetime.combine(_date.fromisoformat(self.date), h)
        except ValueError:
            return None

    def minutes_ecoulees(self, maintenant: datetime | None = None) -> float | None:
        if self.debut is None:
            return None
        ecart = (maintenant or datetime.now()) - self.debut
        return max(0.0, ecart.total_seconds() / 60)

    def etat(self, maintenant: datetime | None = None) -> str:
        minutes = self.minutes_ecoulees(maintenant)
        if minutes is None:
            return NON_DEMARREE
        if minutes >= self.chrono_max_minutes:
            return DEPASSEMENT
        if minutes >= self.chrono_max_minutes - MARGE_VIGILANCE:
            return VIGILANCE
        return EN_COURS

    def demarrer(self, maintenant: datetime | None = None) -> None:
        """Fixe le départ à l'instant présent. Sans effet si déjà démarrée."""
        if self.heure_debut:
            return
        m = maintenant or datetime.now()
        self.date = m.date().isoformat()
        self.heure_debut = m.time().replace(microsecond=0).isoformat()

    def valider(self) -> None:
        if not self.personne_id:
            raise ValueError("Une séance doit être rattachée à une personne.")
        try:
            _date.fromisoformat(self.date)
        except ValueError as exc:
            raise ValueError("Date de séance invalide (AAAA-MM-JJ).") from exc
        if self.heure_debut:
            try:
                time.fromisoformat(self.heure_debut)
            except ValueError as exc:
                raise ValueError("Heure de début invalide (HH:MM ou HH:MM:SS).") from exc
        if self.chrono_max_minutes <= 0:
            raise ValueError("La durée maximale doit être positive.")


def libelle_chrono(seance: Seance, maintenant: datetime | None = None) -> str:
    """Affichage court : « 47 min / 90 min »."""
    minutes = seance.minutes_ecoulees(maintenant)
    if minutes is None:
        return f"non démarrée — plafond {seance.chrono_max_minutes} min"
    return f"{int(minutes)} min / {seance.chrono_max_minutes} min"


# ── CRUD ───────────────────────────────────────────────────────────────────
_COLONNES = "id, personne_id, date, heure_debut, chrono_max_minutes, objectif_texte"


def _depuis_ligne(l) -> Seance:
    return Seance(id=l["id"], personne_id=l["personne_id"], date=l["date"],
                  heure_debut=l["heure_debut"], chrono_max_minutes=l["chrono_max_minutes"],
                  objectif_texte=l["objectif_texte"])


def creer(s: Seance, chemin: Path | str | None = None) -> Seance:
    s.valider()
    with db.connexion(chemin) as cx:
        if not cx.execute("SELECT 1 FROM personne WHERE id = ?", (s.personne_id,)).fetchone():
            raise ValueError("Personne introuvable : séance non créée.")
        cx.execute(f"INSERT INTO seance ({_COLONNES}) VALUES (?,?,?,?,?,?)",
                   (s.id, s.personne_id, s.date, s.heure_debut,
                    s.chrono_max_minutes, s.objectif_texte))
    return s


def lire(seance_id: str, chemin: Path | str | None = None) -> Seance | None:
    with db.connexion(chemin) as cx:
        l = cx.execute(f"SELECT {_COLONNES} FROM seance WHERE id = ?",
                       (seance_id,)).fetchone()
    return _depuis_ligne(l) if l else None


def lister_par_personne(personne_id: str, chemin: Path | str | None = None) -> list[Seance]:
    with db.connexion(chemin) as cx:
        return [_depuis_ligne(l) for l in cx.execute(
            f"SELECT {_COLONNES} FROM seance WHERE personne_id = ? "
            "ORDER BY date DESC, IFNULL(heure_debut,'') DESC", (personne_id,))]


def modifier(s: Seance, chemin: Path | str | None = None) -> Seance:
    s.valider()
    with db.connexion(chemin) as cx:
        cx.execute("UPDATE seance SET date=?, heure_debut=?, chrono_max_minutes=?, "
                   "objectif_texte=? WHERE id=?",
                   (s.date, s.heure_debut, s.chrono_max_minutes, s.objectif_texte, s.id))
    return s


def supprimer(seance_id: str, chemin: Path | str | None = None) -> bool:
    with db.connexion(chemin) as cx:
        c = cx.execute("DELETE FROM seance WHERE id = ?", (seance_id,))
    return c.rowcount > 0
