"""Accès SQLite local. Aucun réseau, aucun cloud."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CHEMIN_BASE = DOSSIER / "md_consulting.db"
CHEMIN_SCHEMA = DOSSIER / "schema.sql"


def connexion(chemin: Path | str | None = None) -> sqlite3.Connection:
    """Ouvre la base et active les clés étrangères (indispensable au CASCADE)."""
    cx = sqlite3.connect(str(chemin or CHEMIN_BASE))
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys = ON")
    return cx


def colonnes(cx: sqlite3.Connection, table: str) -> list[str]:
    return [l["name"] for l in cx.execute(f"PRAGMA table_info({table})")]


def _migrer_fiche_complete(cx: sqlite3.Connection) -> bool:
    """Passe de l'ancienne fiche (pseudonyme) à la fiche complète (nom, prénom).

    Les données existantes sont conservées : l'ancien nom complet, ou à défaut
    le pseudonyme, atterrit dans « nom ». Le prénom reste vide — il sera signalé
    comme manquant plutôt que deviné en coupant une chaîne en deux.
    """
    existantes = colonnes(cx, "personne")
    if not existantes or "pseudonyme" not in existantes or "nom" in existantes:
        return False
    cx.execute("PRAGMA foreign_keys = OFF")
    cx.execute("ALTER TABLE personne RENAME TO personne_ancienne")
    cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
    cx.execute("""
        INSERT INTO personne (id, nom, prenom, tranche_age, public,
                              consentement_parental_date, lien_mescompetences,
                              notes_libres, date_creation)
        SELECT id,
               CASE WHEN IFNULL(TRIM(nom_complet), '') <> '' THEN nom_complet
                    ELSE pseudonyme END,
               '', tranche_age, public, consentement_parental_date,
               lien_mescompetences, notes_libres, date_creation
        FROM personne_ancienne""")
    cx.execute("DROP TABLE personne_ancienne")
    cx.execute("PRAGMA foreign_keys = ON")
    return True


def _migrer_types_de_test_libres(cx: sqlite3.Connection) -> bool:
    """Retire la liste figée de types de test (ancienne contrainte CHECK).

    Les outils d'investigation sont désormais des fichiers ; en ajouter un ne
    doit pas demander de migrer la base.
    """
    ligne = cx.execute("SELECT sql FROM sqlite_master WHERE type='table' "
                       "AND name='resultat_test'").fetchone()
    if not ligne or "CHECK (type_test IN" not in (ligne["sql"] or ""):
        return False
    cx.execute("PRAGMA foreign_keys = OFF")
    cx.execute("ALTER TABLE resultat_test RENAME TO resultat_test_ancien")
    cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
    cx.execute("INSERT INTO resultat_test SELECT id, seance_id, type_test, "
               "reponses_json, synthese_texte, date_saisie FROM resultat_test_ancien")
    cx.execute("DROP TABLE resultat_test_ancien")
    cx.execute("PRAGMA foreign_keys = ON")
    return True


def initialiser(chemin: Path | str | None = None) -> None:
    """Crée les tables si besoin, puis applique les migrations. Idempotent."""
    with connexion(chemin) as cx:
        cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
        _migrer_fiche_complete(cx)
        _migrer_types_de_test_libres(cx)
