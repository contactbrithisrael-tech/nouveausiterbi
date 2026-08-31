"""Parseur EPUB : un bloc par chapitre.

L'EPUB est le format le mieux structuré d'une bibliothèque : les métadonnées
Dublin Core (titre, auteur, langue, éditeur, ISBN, date) sont normalisées et
le découpage en fichiers correspond aux chapitres réels. On en tire donc à la
fois une localisation de qualité (« chapitre ») et un catalogue fiable — deux
choses qu'aucune heuristique sur un PDF ne fournira jamais.

Le HTML est nettoyé sans BeautifulSoup : une seule expression sur des
fichiers déjà bien formés suffit, et cela évite une dépendance de plus dans
le chemin d'ingestion.
"""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path
from typing import Iterator

from app.ingestion.chunker import Bloc

_SCRIPTS_STYLES = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_BALISES_BLOC = re.compile(r"</(p|div|h[1-6]|li|tr|section|article)>", re.I)
_BALISES = re.compile(r"<[^>]+>")
_TITRE_HTML = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.S | re.I)


def _html_vers_texte(brut: bytes) -> tuple[str, str | None]:
    contenu = brut.decode("utf-8", errors="replace")
    contenu = _SCRIPTS_STYLES.sub(" ", contenu)
    titre = None
    m = _TITRE_HTML.search(contenu)
    if m:
        titre = html_module.unescape(_BALISES.sub("", m.group(1))).strip()[:256] or None
    # Les fins de blocs deviennent des sauts de paragraphe AVANT le retrait
    # des balises : sinon tout le chapitre se retrouve sur une seule ligne et
    # le chunker perd sa principale frontière de découpage.
    contenu = _BALISES_BLOC.sub("\n\n", contenu)
    contenu = _BALISES.sub(" ", contenu)
    return html_module.unescape(contenu), titre


def _metadonnee(livre, nom: str) -> str | None:
    try:
        valeurs = livre.get_metadata("DC", nom)
        if valeurs:
            return str(valeurs[0][0]).strip()[:512] or None
    except Exception:
        pass
    return None


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    import ebooklib  # import tardif
    from ebooklib import epub

    livre = epub.read_epub(str(chemin), options={"ignore_ncx": True})

    identifiants = []
    try:
        identifiants = [str(v[0]) for v in (livre.get_metadata("DC", "identifier") or [])]
    except Exception:
        pass
    isbn = next((i.replace("urn:isbn:", "").strip() for i in identifiants if "isbn" in i.lower()), None)

    date = _metadonnee(livre, "date")
    annee = None
    if date:
        m = re.search(r"(1[5-9]\d{2}|20\d{2})", date)
        annee = int(m.group(1)) if m else None

    infos = {
        "title": _metadonnee(livre, "title") or chemin.stem,
        "author": _metadonnee(livre, "creator"),
        "language": _metadonnee(livre, "language"),
        "publisher": _metadonnee(livre, "publisher"),
        "isbn": isbn,
        "year": annee,
    }

    def generer() -> Iterator[Bloc]:
        for element in livre.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            texte, titre_chapitre = _html_vers_texte(element.get_content())
            if texte.strip():
                yield Bloc(texte=texte, section=titre_chapitre, title=infos["title"])

    return generer(), infos
