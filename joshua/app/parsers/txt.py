"""Parseur texte brut.

Le seul point non trivial est l'encodage : une bibliothèque réelle contient
des fichiers en UTF-8, en Latin-1 et en UTF-16 (exports Windows). Échouer sur
l'un d'eux ferait perdre le document entier, alors qu'un décodage tolérant
n'en abîme au pire que quelques caractères.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from app.ingestion.chunker import Bloc

ENCODAGES = ("utf-8", "utf-8-sig", "utf-16", "cp1252", "latin-1")


def lire_texte(chemin: Path) -> str:
    """Lit un fichier en essayant plusieurs encodages, du plus probable au
    plus permissif. ``latin-1`` accepte toute séquence d'octets : c'est le
    filet de sécurité qui garantit qu'aucun fichier n'est perdu."""
    donnees = chemin.read_bytes()
    for encodage in ENCODAGES:
        try:
            return donnees.decode(encodage)
        except (UnicodeDecodeError, LookupError):
            continue
    return donnees.decode("utf-8", errors="replace")


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    texte = lire_texte(chemin)
    # Un fichier texte n'a ni pages ni sections : le chunker s'appuiera sur
    # les paragraphes. Le titre par défaut est le nom du fichier, ce qui vaut
    # mieux qu'aucune référence dans une citation.
    blocs = iter([Bloc(texte=texte, title=chemin.stem)])
    return blocs, {"title": chemin.stem}
