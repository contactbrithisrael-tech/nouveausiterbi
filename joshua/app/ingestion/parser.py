"""Dispatcher de parseurs : extension → module.

Le type est déterminé par l'EXTENSION, pas par le contenu. Une détection par
nombre magique serait plus robuste en théorie, mais impose de lire chaque
fichier avant de savoir s'il est utile — coûteux sur un scan de dizaines de
milliers de fichiers, et sans bénéfice réel : les bibliothèques personnelles
ont des extensions correctes.

Un format inconnu n'est pas une erreur : il est ignoré et compté. Une
bibliothèque contient des couvertures JPEG, des fichiers de métadonnées
Calibre et des `.DS_Store` ; les traiter comme des échecs noierait les vraies
erreurs dans le bruit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterator

from app.ingestion.chunker import Bloc

EXTENSIONS: dict[str, str] = {
    ".pdf": "pdf",
    ".epub": "epub",
    ".docx": "docx",
    ".txt": "txt",
    ".text": "txt",
    ".md": "markdown",
    ".markdown": "markdown",
    ".csv": "csv",
    ".tsv": "csv",
    ".json": "json",
    ".jsonl": "json",
    ".ndjson": "json",
}

MIME_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".epub": "application/epub+zip",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
}


class FormatNonSupporte(Exception):
    """Le fichier n'est pas un document exploitable (image, archive…)."""


def type_document(chemin: Path) -> str | None:
    return EXTENSIONS.get(chemin.suffix.lower())


def mime_type(chemin: Path) -> str:
    return MIME_TYPES.get(chemin.suffix.lower(), "application/octet-stream")


def _charger(nom: str) -> Callable[[Path], tuple[Iterator[Bloc], dict]]:
    """Import du parseur au moment de l'usage.

    pypdf, python-docx et ebooklib ne sont chargés que si un document du
    format correspondant est rencontré : une bibliothèque exclusivement PDF ne
    paie jamais le coût d'import d'ebooklib.
    """
    if nom == "pdf":
        from app.parsers.pdf import parser
    elif nom == "epub":
        from app.parsers.epub import parser
    elif nom == "docx":
        from app.parsers.docx import parser
    elif nom == "markdown":
        from app.parsers.markdown import parser
    elif nom == "csv":
        from app.parsers.csv_parser import parser
    elif nom == "json":
        from app.parsers.json_parser import parser
    else:
        from app.parsers.txt import parser
    return parser


def extraire(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    """Retourne ``(blocs, métadonnées)`` pour un fichier supporté."""
    nom = type_document(chemin)
    if nom is None:
        raise FormatNonSupporte(f"Extension non prise en charge : {chemin.suffix or '(aucune)'}")
    return _charger(nom)(chemin)
