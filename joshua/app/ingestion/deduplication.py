"""Déduplication : empreintes de fichiers et de chunks.

Deux niveaux, pour deux problèmes distincts
-------------------------------------------
1. **Fichier (SHA-256 du contenu binaire).** Répond à « ce fichier a-t-il
   déjà été indexé ? ». L'empreinte porte sur le CONTENU, pas sur le chemin :
   le même livre rangé dans deux dossiers, ou renommé, n'est indexé qu'une
   fois. C'est la garantie qui rend l'ingestion rejouable sans précaution.

2. **Chunk (SHA-256 du texte normalisé).** Répond à « ce passage existe-t-il
   déjà ? ». Sur une bibliothèque réelle, les mêmes préfaces, mentions
   légales et pages de garde reviennent des centaines de fois ; les indexer
   toutes gonfle l'index et sature les résultats de recherche avec du bruit.

Pourquoi SHA-256 et pas plus rapide
-----------------------------------
Le coût du hachage est négligeable devant celui de l'extraction de texte et
de l'encodage. Une fonction non cryptographique (xxHash) économiserait
quelques secondes sur des heures d'ingestion, au prix d'un risque de
collision sur des millions d'entrées. Le compromis n'a aucun intérêt ici.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.security.sanitization import normaliser_texte

#: 1 Mio : compromis entre nombre d'appels système et pic mémoire. Un fichier
#: de 2 Go est haché avec 1 Mio de RAM, ce qui est le point essentiel.
TAILLE_BLOC = 1024 * 1024


def checksum_fichier(chemin: str | Path, taille_bloc: int = TAILLE_BLOC) -> str:
    """SHA-256 d'un fichier, lu en flux.

    Jamais ``read()`` intégral : la bibliothèque contient des PDF de plusieurs
    centaines de mégaoctets, et l'ingestion doit tourner sur une machine
    ordinaire pendant que le bot répond.
    """
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        while bloc := f.read(taille_bloc):
            h.update(bloc)
    return h.hexdigest()


def checksum_texte(texte: str) -> str:
    """SHA-256 d'un texte, après normalisation.

    La normalisation est indispensable : deux extractions du même passage
    diffèrent souvent par des espaces ou des variantes Unicode, et produiraient
    sinon deux empreintes différentes pour un contenu identique.
    """
    return hashlib.sha256(normaliser_texte(texte).encode("utf-8")).hexdigest()


class DeduplicateurChunks:
    """Filtre les chunks déjà vus pendant une session d'ingestion.

    L'état est volontairement EN MÉMOIRE et non persisté : sur un import de
    plusieurs millions de chunks, un ensemble d'empreintes hexadécimales
    représente environ 100 octets par entrée, soit quelques centaines de Mo au
    pire — acceptable. Le persister imposerait une requête par chunk, c'est-à-dire
    exactement le schéma d'accès que l'ingestion massive doit éviter.

    ``max_entrees`` borne cette croissance : au-delà, le filtre se désactive
    plutôt que d'épuiser la mémoire. Perdre la déduplication est un moindre
    mal comparé à une ingestion interrompue à 80 %.
    """

    def __init__(self, max_entrees: int = 5_000_000) -> None:
        self._vus: set[str] = set()
        self._max = max_entrees
        self._sature = False
        self.doublons = 0

    def est_nouveau(self, texte: str) -> bool:
        if self._sature:
            return True
        empreinte = checksum_texte(texte)
        if empreinte in self._vus:
            self.doublons += 1
            return False
        self._vus.add(empreinte)
        if len(self._vus) >= self._max:
            self._sature = True
        return True

    @property
    def taille(self) -> int:
        return len(self._vus)


def fichier_inchange(chemin: Path, checksum_connu: str | None, mtime_connu: float | None) -> bool:
    """Décide si un fichier peut être ignoré SANS le lire entièrement.

    Ordre des vérifications, du moins cher au plus cher :
    ``mtime`` (un ``stat``) avant ``checksum`` (une lecture complète). Sur une
    bibliothèque de 50 000 livres dont 3 ont changé, cela évite 49 997
    lectures intégrales — la différence entre un scan de quelques secondes et
    un scan de plusieurs dizaines de minutes.

    Le ``mtime`` seul ne suffirait pas (il peut être réécrit sans changement
    de contenu, ou l'inverse après une synchronisation iCloud) : il sert
    d'accélérateur, l'empreinte reste l'autorité.
    """
    if checksum_connu is None:
        return False
    try:
        mtime_actuel = chemin.stat().st_mtime
    except OSError:
        return False
    if mtime_connu is not None and abs(mtime_actuel - mtime_connu) < 1.0:
        return True
    return checksum_fichier(chemin) == checksum_connu
