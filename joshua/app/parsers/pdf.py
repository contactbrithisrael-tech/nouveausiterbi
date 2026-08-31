"""Parseur PDF, page par page.

Choix d'architecture
--------------------
* **pypdf, en flux.** Le fichier reste ouvert et les pages sont produites une
  à une : un ouvrage de 900 pages ne charge jamais son texte intégral en
  mémoire. C'est ce qui rend l'ingestion d'une bibliothèque tenable.

* **Le numéro de page est l'information la plus précieuse.** C'est elle qui
  rend une citation vérifiable (« Manuel_X.pdf — page 47 »). Elle est donc
  portée par chaque bloc, dès l'extraction.

* **Aucune OCR ici.** Un PDF scanné sans couche texte produit des pages
  vides ; il est signalé comme tel plutôt que traité silencieusement. Ajouter
  l'OCR (Tesseract) est un choix d'infrastructure à part entière — plusieurs
  secondes par page et une dépendance système — qui n'a pas sa place dans le
  chemin d'ingestion par défaut. Le README documente le branchement.

* **Une page illisible n'interrompt pas le document.** Les PDF réels
  contiennent des pages corrompues ; perdre un livre entier pour une page
  serait absurde.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from app.ingestion.chunker import Bloc
from app.utils.logging import get_logger

log = get_logger(__name__)


def _metadonnees(lecteur) -> dict:
    """Métadonnées du PDF, défensivement.

    Les champs XMP/Info sont souvent absents, parfois de types inattendus :
    tout est converti en chaîne et les échecs sont ignorés, ces informations
    étant un bonus et non une condition d'indexation.
    """
    infos: dict = {}
    try:
        brut = lecteur.metadata or {}
        for cle_pdf, cle in (("/Title", "title"), ("/Author", "author"), ("/Producer", "publisher")):
            valeur = brut.get(cle_pdf)
            if valeur:
                infos[cle] = str(valeur).strip()[:512]
    except Exception:
        pass
    return infos


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    from pypdf import PdfReader  # import tardif : dépendance lourde

    lecteur = PdfReader(str(chemin))
    infos = _metadonnees(lecteur)
    infos.setdefault("title", chemin.stem)
    infos["pages"] = len(lecteur.pages)

    def generer() -> Iterator[Bloc]:
        pages_vides = 0
        for numero, page in enumerate(lecteur.pages, start=1):
            try:
                texte = page.extract_text() or ""
            except Exception as exc:
                log.warning("pdf_page_illisible", file=chemin.name, page=numero, error=str(exc))
                continue
            if not texte.strip():
                pages_vides += 1
                continue
            yield Bloc(texte=texte, page=numero, title=infos.get("title"))
        if pages_vides and pages_vides == infos["pages"]:
            log.warning("pdf_sans_couche_texte", file=chemin.name, pages=pages_vides)

    return generer(), infos
