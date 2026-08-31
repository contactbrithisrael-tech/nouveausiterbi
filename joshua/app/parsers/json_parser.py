"""Parseur JSON : aplatissement en lignes « chemin : valeur ».

Un JSON injecté tel quel dans un embedding encode surtout sa syntaxe
(accolades, guillemets) et très peu son sens. On l'aplatit donc en chemins
lisibles (« client.adresse.ville : Paris »), forme qui se rapproche d'une
phrase et que le modèle sait rapprocher d'une question en langage naturel.

Le JSON Lines est détecté et traité comme un flux d'objets : c'est le format
d'export le plus courant pour les gros volumes, et le charger d'un bloc
supposerait qu'il tient en mémoire.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from app.ingestion.chunker import Bloc
from app.parsers.txt import lire_texte

ENTREES_PAR_BLOC = 25
PROFONDEUR_MAX = 8  # garde-fou contre les structures pathologiques


def _aplatir(valeur: Any, prefixe: str = "", profondeur: int = 0) -> Iterator[str]:
    if profondeur > PROFONDEUR_MAX:
        return
    if isinstance(valeur, dict):
        for cle, sous_valeur in valeur.items():
            yield from _aplatir(sous_valeur, f"{prefixe}.{cle}" if prefixe else str(cle), profondeur + 1)
    elif isinstance(valeur, list):
        for i, element in enumerate(valeur):
            yield from _aplatir(element, f"{prefixe}[{i}]", profondeur + 1)
    elif valeur not in (None, "", []):
        yield f"{prefixe} : {valeur}"


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    texte = lire_texte(chemin)
    lignes = texte.strip().splitlines()
    est_jsonl = len(lignes) > 1 and lignes[0].lstrip().startswith("{") and not texte.lstrip().startswith("[")

    def generer() -> Iterator[Bloc]:
        tampon: list[str] = []
        compteur = 0
        sources: Iterator[Any]
        if est_jsonl:
            def flux() -> Iterator[Any]:
                for ligne in lignes:
                    ligne = ligne.strip()
                    if not ligne:
                        continue
                    try:
                        yield json.loads(ligne)
                    except json.JSONDecodeError:
                        # Une ligne corrompue au milieu d'un export de plusieurs
                        # millions d'entrées ne doit pas condamner le fichier.
                        continue
            sources = flux()
        else:
            donnees = json.loads(texte)
            sources = iter(donnees if isinstance(donnees, list) else [donnees])

        for entree in sources:
            lignes_plates = list(_aplatir(entree))
            if lignes_plates:
                tampon.append("\n".join(lignes_plates))
                compteur += 1
            if len(tampon) >= ENTREES_PAR_BLOC:
                yield Bloc(texte="\n\n".join(tampon), title=chemin.stem, section=f"entrées ~{compteur}")
                tampon = []
        if tampon:
            yield Bloc(texte="\n\n".join(tampon), title=chemin.stem)

    return generer(), {"title": chemin.stem, "jsonl": est_jsonl}
