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


def _migrer_publics_libres(cx: sqlite3.Connection) -> bool:
    """Retire la liste figée de publics (ancienne contrainte CHECK)."""
    ligne = cx.execute("SELECT sql FROM sqlite_master WHERE type='table' "
                       "AND name='personne'").fetchone()
    if not ligne or "CHECK (public IN" not in (ligne["sql"] or ""):
        return False
    colonnes_actuelles = ", ".join(colonnes(cx, "personne"))
    cx.execute("PRAGMA foreign_keys = OFF")
    cx.execute("ALTER TABLE personne RENAME TO personne_ancienne")
    cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
    cx.execute(f"INSERT INTO personne ({colonnes_actuelles}) "
               f"SELECT {colonnes_actuelles} FROM personne_ancienne")
    cx.execute("DROP TABLE personne_ancienne")
    cx.execute("PRAGMA foreign_keys = ON")
    return True


def _a_index_unique(cx: sqlite3.Connection, table: str, colonne: str) -> bool:
    """Teste la contrainte telle que SQLite la connaît, et non l'orthographe
    du DDL : un espace de plus ne doit pas faire croire qu'elle manque."""
    for index in cx.execute(f"PRAGMA index_list({table})"):
        if not index["unique"]:
            continue
        noms = [c["name"] for c in cx.execute(f"PRAGMA index_info({index['name']})")]
        if noms == [colonne]:
            return True
    return False


def _migrer_un_rapport_par_seance(cx: sqlite3.Connection) -> bool:
    """Ajoute l'unicité du compte rendu par séance, en ne gardant que le
    plus récent lorsque plusieurs coexistaient."""
    anciennes = colonnes(cx, "rapport")
    if not anciennes or _a_index_unique(cx, "rapport", "seance_id"):
        return False
    cx.execute("PRAGMA foreign_keys = OFF")
    cx.execute("ALTER TABLE rapport RENAME TO rapport_ancien")
    cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
    # On ne reprend que les colonnes que l'ancienne table portait réellement :
    # le schéma a pu gagner des blocs entre-temps.
    liste = ", ".join(c for c in anciennes if c in colonnes(cx, "rapport"))
    cx.execute(f"""
        INSERT INTO rapport ({liste}) SELECT {liste} FROM rapport_ancien
        WHERE id IN (
            SELECT id FROM rapport_ancien r WHERE r.date_generation = (
                SELECT MAX(date_generation) FROM rapport_ancien
                WHERE seance_id = r.seance_id)
            GROUP BY r.seance_id)""")
    cx.execute("DROP TABLE rapport_ancien")
    cx.execute("PRAGMA foreign_keys = ON")
    return True


def _migrer_blocs_du_rapport(cx: sqlite3.Connection) -> bool:
    """Ajoute les blocs Pistes, Compétences et Références aux comptes rendus
    existants. Un simple ajout de colonnes : rien n'est perdu."""
    existantes = colonnes(cx, "rapport")
    if not existantes:
        return False
    ajoutes = False
    for colonne in ("bloc_pistes", "bloc_competences", "bloc_references"):
        if colonne not in existantes:
            cx.execute(f"ALTER TABLE rapport ADD COLUMN {colonne} TEXT")
            ajoutes = True
    return ajoutes


def initialiser(chemin: Path | str | None = None) -> None:
    """Crée les tables si besoin, puis applique les migrations. Idempotent."""
    with connexion(chemin) as cx:
        cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
        _migrer_fiche_complete(cx)
        _migrer_publics_libres(cx)
        _migrer_types_de_test_libres(cx)
        _migrer_un_rapport_par_seance(cx)
        _migrer_blocs_du_rapport(cx)
