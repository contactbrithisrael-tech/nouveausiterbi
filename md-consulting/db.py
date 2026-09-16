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


def initialiser(chemin: Path | str | None = None) -> None:
    """Crée les tables si elles n'existent pas. Idempotent."""
    with connexion(chemin) as cx:
        cx.executescript(CHEMIN_SCHEMA.read_text(encoding="utf-8"))
