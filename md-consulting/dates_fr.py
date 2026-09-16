"""Affichage des dates au format français. Le stockage reste en ISO 8601."""
from __future__ import annotations

from datetime import datetime


def jour(iso: str | None) -> str:
    """'2026-09-10' ou '2026-09-10T14:03:00' → '10/09/2026'."""
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except ValueError:
        return iso


def jour_heure(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y à %H:%M")
    except ValueError:
        return iso
