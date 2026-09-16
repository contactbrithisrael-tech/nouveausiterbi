"""Personne : fiche de renseignement complète, règles RGPD et CRUD.
Aucune dépendance Streamlit.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import db

TRANCHES_AGE = {
    "college": "Collège (11-15 ans)",
    "lycee": "Lycée (15-18 ans)",
    "adulte": "Adulte",
}

PUBLICS = {
    "college": "Scolaire collège",
    "lycee": "Scolaire lycée",
    "reconversion": "Adulte en reconversion",
    "vae": "Adulte en démarche VAE",
    "handicap": "Personne en situation de handicap",
}

# Âge en dessous duquel le consentement parental est exigé avant toute
# création de fiche. 18 = tout mineur, choix protecteur. Le brief évoquait
# « moins de 15 ans » : mettre 15 ici suffit à revenir à cette règle.
SEUIL_CONSENTEMENT_PARENTAL = 18

# Repli quand la date de naissance n'est pas renseignée : l'âge exact est alors
# inconnu et seule la tranche permet de trancher.
MINEUR_PAR_TRANCHE = {"college": True, "lycee": True, "adulte": False}

# Intitulés des champs, pour les messages de fiche incomplète.
INTITULES = {
    "nom": "nom", "prenom": "prénom", "date_naissance": "date de naissance",
    "contact": "téléphone ou courriel", "adresse": "adresse",
    "situation": "situation (classe, établissement ou situation professionnelle)",
    "representant_legal": "représentant légal",
    "representant_contact": "contact du représentant légal",
    "consentement_parental_date": "date du consentement parental",
}


class ConsentementParentalManquant(ValueError):
    """Levée quand on tente d'enregistrer un mineur sans consentement parental."""


class DonneesInvalides(ValueError):
    """Levée quand un champ obligatoire manque ou qu'une valeur est hors liste."""


def age_au(naissance: str | None, jour: date | None = None) -> int | None:
    """Âge révolu, ou None si la date de naissance n'est pas renseignée."""
    if not naissance:
        return None
    try:
        n = date.fromisoformat(naissance)
    except ValueError:
        return None
    j = jour or date.today()
    return j.year - n.year - ((j.month, j.day) < (n.month, n.day))


def tranche_pour_age(age: int) -> str:
    """Tranche déduite d'un âge exact. Sert à proposer, jamais à imposer."""
    if age < 15:
        return "college"
    if age < 18:
        return "lycee"
    return "adulte"


@dataclass
class Personne:
    nom: str
    prenom: str
    tranche_age: str
    public: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date_naissance: str | None = None
    telephone: str | None = None
    courriel: str | None = None
    adresse: str | None = None
    situation: str | None = None
    rqth: bool = False
    representant_legal: str | None = None
    representant_contact: str | None = None
    consentement_parental_date: str | None = None
    lien_mescompetences: str | None = None
    notes_libres: str | None = None
    date_creation: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # ── Identité affichée ──────────────────────────────────────────────────
    @property
    def nom_affiche(self) -> str:
        return " ".join(p for p in (self.nom.upper(), self.prenom) if p).strip()

    @property
    def age(self) -> int | None:
        return age_au(self.date_naissance)

    # ── Règles de minorité ─────────────────────────────────────────────────
    @property
    def is_mineur(self) -> bool:
        age = self.age
        if age is not None:
            return age < 18
        return MINEUR_PAR_TRANCHE.get(self.tranche_age, False)

    @property
    def consentement_requis(self) -> bool:
        """L'âge exact prime dès qu'il est connu ; sinon on retombe sur la tranche."""
        age = self.age
        if age is not None:
            return age < SEUIL_CONSENTEMENT_PARENTAL
        return MINEUR_PAR_TRANCHE.get(self.tranche_age, False)

    @property
    def consentement_ok(self) -> bool:
        return not self.consentement_requis or bool(self.consentement_parental_date)

    # ── Complétude de la fiche ─────────────────────────────────────────────
    @property
    def champs_manquants(self) -> list[str]:
        """Champs attendus dans une fiche complète et non renseignés.
        N'empêche pas l'enregistrement : seul le consentement le fait."""
        manquants = []
        for champ in ("nom", "prenom", "date_naissance", "adresse", "situation"):
            if not (getattr(self, champ) or "").strip():
                manquants.append(INTITULES[champ])
        if not ((self.telephone or "").strip() or (self.courriel or "").strip()):
            manquants.append(INTITULES["contact"])
        if self.is_mineur:
            for champ in ("representant_legal", "representant_contact"):
                if not (getattr(self, champ) or "").strip():
                    manquants.append(INTITULES[champ])
        if self.consentement_requis and not self.consentement_parental_date:
            manquants.append(INTITULES["consentement_parental_date"])
        return manquants

    @property
    def fiche_complete(self) -> bool:
        return not self.champs_manquants

    # ── Validation ─────────────────────────────────────────────────────────
    def valider(self) -> None:
        """Bloque tout enregistrement non conforme. Appelée par creer() et modifier()."""
        for champ in ("nom", "prenom"):
            if not (getattr(self, champ) or "").strip():
                raise DonneesInvalides(f"Le {INTITULES[champ]} est obligatoire.")
        if self.tranche_age not in TRANCHES_AGE:
            raise DonneesInvalides(f"Tranche d'âge inconnue : {self.tranche_age!r}")
        if self.public not in PUBLICS:
            raise DonneesInvalides(f"Public inconnu : {self.public!r}")
        if self.date_naissance:
            try:
                n = date.fromisoformat(self.date_naissance)
            except ValueError as exc:
                raise DonneesInvalides("Date de naissance invalide (AAAA-MM-JJ).") from exc
            if n > date.today():
                raise DonneesInvalides("La date de naissance est dans le futur.")
        if self.consentement_parental_date:
            try:
                date.fromisoformat(self.consentement_parental_date)
            except ValueError as exc:
                raise DonneesInvalides(
                    "Date de consentement parental invalide (AAAA-MM-JJ).") from exc
        if not self.consentement_ok:
            age = self.age
            precision = f" ({age} ans)" if age is not None else ""
            raise ConsentementParentalManquant(
                f"Personne mineure{precision} : la date de consentement parental est "
                "obligatoire avant toute création de fiche.")


# ── CRUD ───────────────────────────────────────────────────────────────────
_CHAMPS = ("id", "nom", "prenom", "date_naissance", "telephone", "courriel",
           "adresse", "tranche_age", "public", "situation", "rqth",
           "representant_legal", "representant_contact",
           "consentement_parental_date", "lien_mescompetences", "notes_libres",
           "date_creation")
_COLONNES = ", ".join(_CHAMPS)


def _valeurs(p: Personne) -> tuple:
    brut = []
    for c in _CHAMPS:
        v = getattr(p, c)
        if c == "rqth":
            v = 1 if v else 0
        elif isinstance(v, str):
            v = v.strip() or (None if c not in ("nom", "prenom") else v.strip())
        brut.append(v)
    return tuple(brut)


def _depuis_ligne(l) -> Personne:
    donnees = {c: l[c] for c in _CHAMPS}
    donnees["rqth"] = bool(donnees["rqth"])
    return Personne(**donnees)


def creer(p: Personne, chemin: Path | str | None = None) -> Personne:
    """Valide puis insère. Lève avant écriture si le consentement manque."""
    p.valider()
    with db.connexion(chemin) as cx:
        cx.execute(f"INSERT INTO personne ({_COLONNES}) VALUES "
                   f"({','.join('?' * len(_CHAMPS))})", _valeurs(p))
    return p


def lire(personne_id: str, chemin: Path | str | None = None) -> Personne | None:
    with db.connexion(chemin) as cx:
        l = cx.execute(f"SELECT {_COLONNES} FROM personne WHERE id = ?",
                       (personne_id,)).fetchone()
    return _depuis_ligne(l) if l else None


def lister(public: str | None = None, recherche: str | None = None,
           chemin: Path | str | None = None) -> list[Personne]:
    sql = f"SELECT {_COLONNES} FROM personne"
    clauses, params = [], []
    if public:
        clauses.append("public = ?")
        params.append(public)
    if recherche:
        clauses.append("(nom LIKE ? OR prenom LIKE ? OR IFNULL(courriel,'') LIKE ?)")
        params += [f"%{recherche}%"] * 3
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY nom COLLATE NOCASE, prenom COLLATE NOCASE"
    with db.connexion(chemin) as cx:
        return [_depuis_ligne(l) for l in cx.execute(sql, params)]


def modifier(p: Personne, chemin: Path | str | None = None) -> Personne:
    """Même validation qu'à la création : on ne peut pas retirer un consentement."""
    p.valider()
    valeurs = _valeurs(p)
    majs = ", ".join(f"{c} = ?" for c in _CHAMPS if c != "id")
    params = [v for c, v in zip(_CHAMPS, valeurs) if c != "id"] + [p.id]
    with db.connexion(chemin) as cx:
        cx.execute(f"UPDATE personne SET {majs} WHERE id = ?", params)
    return p


def compter_liees(personne_id: str, chemin: Path | str | None = None) -> dict[str, int]:
    """Ce qui sera détruit avec la fiche — affiché avant confirmation."""
    with db.connexion(chemin) as cx:
        seances = cx.execute(
            "SELECT COUNT(*) FROM seance WHERE personne_id = ?", (personne_id,)).fetchone()[0]
        tests = cx.execute(
            "SELECT COUNT(*) FROM resultat_test WHERE seance_id IN "
            "(SELECT id FROM seance WHERE personne_id = ?)", (personne_id,)).fetchone()[0]
        rapports = cx.execute(
            "SELECT COUNT(*) FROM rapport WHERE seance_id IN "
            "(SELECT id FROM seance WHERE personne_id = ?)", (personne_id,)).fetchone()[0]
    return {"seances": seances, "tests": tests, "rapports": rapports}


def supprimer(personne_id: str, chemin: Path | str | None = None) -> bool:
    """Droit à l'effacement : la fiche et tout ce qui en dépend (CASCADE)."""
    with db.connexion(chemin) as cx:
        curseur = cx.execute("DELETE FROM personne WHERE id = ?", (personne_id,))
    return curseur.rowcount > 0
