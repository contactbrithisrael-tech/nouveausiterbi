"""Parseur Markdown : la structure de titres devient la localisation.

Le Markdown est le seul format où la hiérarchie est explicite et fiable. On
l'exploite pour renseigner ``section`` : les citations deviennent alors
« Guide.md — Installation » au lieu du seul nom de fichier, ce qui change
tout pour l'utilisateur qui veut vérifier une réponse.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from app.ingestion.chunker import Bloc
from app.parsers.txt import lire_texte

_TITRE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$", re.M)


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    texte = lire_texte(chemin)
    titres = list(_TITRE.finditer(texte))
    titre_document = titres[0].group(2) if titres and len(titres[0].group(1)) == 1 else chemin.stem

    def generer() -> Iterator[Bloc]:
        if not titres:
            yield Bloc(texte=texte, title=titre_document)
            return
        # Le texte précédant le premier titre n'appartient à aucune section
        # mais reste du contenu : le perdre amputerait les préambules.
        if titres[0].start() > 0:
            entete = texte[: titres[0].start()].strip()
            if entete:
                yield Bloc(texte=entete, title=titre_document)
        for i, m in enumerate(titres):
            debut = m.end()
            fin = titres[i + 1].start() if i + 1 < len(titres) else len(texte)
            corps = texte[debut:fin].strip()
            if corps:
                yield Bloc(texte=corps, section=m.group(2), title=titre_document)

    return generer(), {"title": titre_document}
