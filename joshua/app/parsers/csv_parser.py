"""Parseur CSV : chaque ligne devient une phrase « colonne : valeur ».

Pourquoi cette forme
--------------------
Un CSV brut (« a,b,c ») produit des embeddings inexploitables : les valeurs
perdent le nom de leur colonne, et la recherche sémantique n'a plus rien à
quoi s'accrocher. Réécrire chaque ligne en « Nom : Dupont | Ville : Paris »
restitue le contexte que l'en-tête portait, au prix d'une légère
redondance — largement rentable pour le RAG.

Les lignes sont groupées par paquets : une ligne isolée serait un chunk
minuscule, et des millions de chunks minuscules ruineraient à la fois la
qualité de recherche et le volume de l'index.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from app.ingestion.chunker import Bloc
from app.parsers.txt import lire_texte

LIGNES_PAR_BLOC = 40


def parser(chemin: Path) -> tuple[Iterator[Bloc], dict]:
    texte = lire_texte(chemin)
    # Sniffer plutôt qu'une virgule imposée : les exports français utilisent
    # massivement le point-virgule.
    try:
        dialecte = csv.Sniffer().sniff(texte[:8192], delimiters=",;\t|")
    except csv.Error:
        dialecte = csv.excel  # type: ignore[assignment]

    lecteur = csv.DictReader(texte.splitlines(), dialect=dialecte)
    colonnes = lecteur.fieldnames or []

    def generer() -> Iterator[Bloc]:
        tampon: list[str] = []
        premiere_ligne = 1
        for numero, ligne in enumerate(lecteur, start=1):
            morceaux = [
                f"{cle} : {str(valeur).strip()}"
                for cle, valeur in ligne.items()
                if cle and valeur and str(valeur).strip()
            ]
            if morceaux:
                tampon.append(" | ".join(morceaux) + ".")
            if len(tampon) >= LIGNES_PAR_BLOC:
                yield Bloc(
                    texte="\n".join(tampon),
                    title=chemin.stem,
                    section=f"lignes {premiere_ligne}–{numero}",
                )
                tampon = []
                premiere_ligne = numero + 1
        if tampon:
            yield Bloc(texte="\n".join(tampon), title=chemin.stem, section=f"lignes {premiere_ligne}+")

    return generer(), {"title": chemin.stem, "columns": colonnes}
