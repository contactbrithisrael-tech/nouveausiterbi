"""Écriture de fichiers .docx avec la seule bibliothèque standard.

Un .docx est une archive ZIP contenant du XML. python-docx ferait le même
travail, mais l'ajouter obligerait à installer une dépendance pour produire
quatre blocs de texte et deux tableaux. Ici : zipfile + xml, rien d'autre.
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

_BORDURES = ("<w:tblBorders>" + "".join(
    f'<w:{c} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
    for c in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>")


def _run(texte: str, gras=False, taille=None, couleur=None) -> str:
    props = ""
    if gras:
        props += "<w:b/>"
    if couleur:
        props += f'<w:color w:val="{couleur}"/>'
    if taille:
        props += f'<w:sz w:val="{taille * 2}"/><w:szCs w:val="{taille * 2}"/>'
    props = f"<w:rPr>{props}</w:rPr>" if props else ""
    # xml:space préserve les espaces de début et de fin
    return (f"<w:r>{props}<w:t xml:space=\"preserve\">{escape(texte)}</w:t></w:r>")


class Document:
    def __init__(self) -> None:
        self._corps: list[str] = []

    def paragraphe(self, texte: str = "", gras=False, taille=None,
                   couleur=None, centre=False) -> "Document":
        pr = '<w:pPr><w:jc w:val="center"/></w:pPr>' if centre else ""
        contenu = _run(texte, gras, taille, couleur) if texte else ""
        self._corps.append(f"<w:p>{pr}{contenu}</w:p>")
        return self

    def titre(self, texte: str, niveau: int = 1) -> "Document":
        tailles = {1: 18, 2: 14, 3: 12}
        self.paragraphe()
        return self.paragraphe(texte, gras=True, taille=tailles.get(niveau, 12),
                               couleur="1F3864" if niveau == 1 else "2E5496")

    def puces(self, lignes: list[str]) -> "Document":
        for l in lignes:
            self.paragraphe(f"•  {l}")
        return self

    def tableau(self, entetes: list[str], lignes: list[list[str]]) -> "Document":
        largeur = max(1, len(entetes))
        grille = "".join(f'<w:gridCol w:w="{9000 // largeur}"/>' for _ in range(largeur))
        def cellule(txt, gras=False):
            return (f'<w:tc><w:tcPr><w:tcW w:w="{9000 // largeur}" w:type="dxa"/></w:tcPr>'
                    f"<w:p>{_run(str(txt), gras=gras)}</w:p></w:tc>")
        trs = ["<w:tr>" + "".join(cellule(e, True) for e in entetes) + "</w:tr>"]
        for ligne in lignes:
            cells = list(ligne) + [""] * (largeur - len(ligne))
            trs.append("<w:tr>" + "".join(cellule(c) for c in cells[:largeur]) + "</w:tr>")
        self._corps.append(
            f'<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/>{_BORDURES}</w:tblPr>'
            f"<w:tblGrid>{grille}</w:tblGrid>" + "".join(trs) + "</w:tbl>")
        return self.paragraphe()

    def _document_xml(self) -> str:
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<w:document xmlns:w="{W}"><w:body>' + "".join(self._corps) +
                '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>'
                "</w:sectPr></w:body></w:document>")

    def enregistrer(self, chemin: Path | str) -> Path:
        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _CONTENT_TYPES)
            z.writestr("_rels/.rels", _RELS)
            z.writestr("word/document.xml", self._document_xml())
        return chemin
