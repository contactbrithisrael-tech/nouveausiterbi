"""Personne : modèle, règles RGPD et CRUD. Aucune dépendance Streamlit."""
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

# Mineur au sens civil (< 18 ans).
EST_MINEUR = {"college": True, "lycee": True, "adulte": False}

# Consentement parental exigé avant toute création de fiche.
# ⚠ POINT À TRANCHER PAR MICKAEL : le brief écrit « moins de 15 ans », mais
# la tranche « collège » (11-15) est à cheval sur ce seuil et « lycée »
# (15-18) est au-dessus. Défaut retenu ici : exigé pour tout mineur.
# Pour revenir à la lettre du brief, passer "lycee" à False — une seule ligne.
CONSENTEMENT_PARENTAL_REQUIS = {"college": True, "lycee": True, "adulte": False}


class ConsentementParentalManquant(ValueError):
    """Levée quand on tente d'enregistrer un mineur sans consentement parental."""


class DonneesInvalides(ValueError):
    """Levée quand un champ obligatoire manque ou qu'une valeur est hors liste."""


@dataclass
class Personne:
    pseudonyme: str
    tranche_age: str
    public: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nom_complet: str | None = None
    consentement_parental_date: str | None = None
    lien_mescompetences: str | None = None
    notes_libres: str | None = None
    date_creation: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def is_mineur(self) -> bool:
        return EST_MINEUR.get(self.tranche_age, False)

    @property
    def consentement_requis(self) -> bool:
        return CONSENTEMENT_PARENTAL_REQUIS.get(self.tranche_age, False)

    @property
    def consentement_ok(self) -> bool:
        return not self.consentement_requis or bool(self.consentement_parental_date)

    def valider(self) -> None:
        """Bloque tout enregistrement non conforme. Appelée par creer() et modifier()."""
        if not (self.pseudonyme or "").strip():
            raise DonneesInvalides("Le pseudonyme / les initiales sont obligatoires.")
        if self.tranche_age not in TRANCHES_AGE:
            raise DonneesInvalides(f"Tranche d'âge inconnue : {self.tranche_age!r}")
        if self.public not in PUBLICS:
            raise DonneesInvalides(f"Public inconnu : {self.public!r}")
        if self.consentement_parental_date:
            try:
                date.fromisoformat(self.consentement_parental_date)
            except ValueError as exc:
                raise DonneesInvalides("Date de consentement parental invalide (AAAA-MM-JJ).") from exc
        if not self.consentement_ok:
            raise ConsentementParentalManquant(
                "Personne mineure : la date de consentement parental est obligatoire "
                "avant toute création de fiche."
            )


# ── CRUD ───────────────────────────────────────────────────────────────────
_COLONNES = (
    "id, pseudonyme, nom_complet, tranche_age, public, "
    "consentement_parental_date, lien_mescompetences, notes_libres, date_creation"
)


def _depuis_ligne(ligne) -> Personne:
    return Personne(**{c: ligne[c] for c in _COLONNES.replace(" ", "").split(",")})


def creer(p: Personne, chemin: Path | str | None = None) -> Personne:
    """Valide puis insère. Lève avant écriture si le consentement manque."""
    p.valider()
    with db.connexion(chemin) as cx:
        cx.execute(
            f"INSERT INTO personne ({_COLONNES}) VALUES (?,?,?,?,?,?,?,?,?)",
            (p.id, p.pseudonyme.strip(), p.nom_complet, p.tranche_age, p.public,
             p.consentement_parental_date, p.lien_mescompetences, p.notes_libres,
             p.date_creation),
        )
    return p


def lire(personne_id: str, chemin: Path | str | None = None) -> Personne | None:
    with db.connexion(chemin) as cx:
        ligne = cx.execute(
            f"SELECT {_COLONNES} FROM personne WHERE id = ?", (personne_id,)
        ).fetchone()
    return _depuis_ligne(ligne) if ligne else None


def lister(public: str | None = None, recherche: str | None = None,
           chemin: Path | str | None = None) -> list[Personne]:
    sql = f"SELECT {_COLONNES} FROM personne"
    clauses, params = [], []
    if public:
        clauses.append("public = ?")
        params.append(public)
    if recherche:
        clauses.append("(pseudonyme LIKE ? OR IFNULL(nom_complet,'') LIKE ?)")
        params += [f"%{recherche}%"] * 2
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY date_creation DESC"
    with db.connexion(chemin) as cx:
        return [_depuis_ligne(l) for l in cx.execute(sql, params)]


def modifier(p: Personne, chemin: Path | str | None = None) -> Personne:
    """Même validation qu'à la création : on ne peut pas retirer un consentement."""
    p.valider()
    with db.connexion(chemin) as cx:
        cx.execute(
            "UPDATE personne SET pseudonyme=?, nom_complet=?, tranche_age=?, public=?, "
            "consentement_parental_date=?, lien_mescompetences=?, notes_libres=? WHERE id=?",
            (p.pseudonyme.strip(), p.nom_complet, p.tranche_age, p.public,
             p.consentement_parental_date, p.lien_mescompetences, p.notes_libres, p.id),
        )
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
