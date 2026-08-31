"""Découverte des fichiers, y compris dans une bibliothèque iCloud Drive.

Le cas iCloud
-------------
macOS affiche dans le Finder des fichiers qui ne sont PAS sur le disque :
seul un fichier fantôme « .Livre.pdf.icloud » de quelques centaines d'octets
existe localement, le contenu restant dans le nuage. Une ingestion naïve
« voit » alors le livre, échoue à l'ouvrir, et le compte en erreur.

Deux vérifications sont faites, et deux seulement :

1. le nom commence par un point et finit par ``.icloud`` — cas explicite ;
2. un fichier fantôme homonyme existe à côté — l'original n'est pas là.

Une troisième heuristique était tentante — « taille nulle = non téléchargé » —
mais elle est fausse : un fichier réellement vide est fréquent et serait
signalé à tort comme bloqué dans le nuage, en attente d'un rapatriement qui
n'arrivera jamais. Les fichiers vides sont donc simplement ignorés, ce qu'ils
méritent : il n'y a rien à indexer dedans.

Ces fichiers sont signalés ``icloud_not_downloaded``, jamais comptés en
erreur, et JAMAIS téléchargés d'autorité : forcer le rapatriement d'une
bibliothèque de 200 Go sur un disque qui ne peut pas l'accueillir serait
une décision que le programme n'a pas à prendre.

Rien n'est modifié dans la bibliothèque source : ce module n'ouvre les
fichiers qu'en lecture, et ne renomme, ne déplace ni ne supprime jamais rien.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from app.ingestion.parser import type_document
from app.utils.logging import get_logger

log = get_logger(__name__)

#: Dossiers à ne jamais parcourir : métadonnées système et artefacts d'outils.
DOSSIERS_IGNORES = {
    ".git", "__pycache__", ".Trash", ".DS_Store", "node_modules",
    ".calibre", ".caltrash", "@eaDir", ".Spotlight-V100", ".fseventsd",
}


@dataclass(slots=True)
class FichierDecouvert:
    chemin: Path
    chemin_relatif: str
    taille: int
    mtime: float
    document_type: str
    #: Vrai si le contenu n'est pas présent localement (iCloud).
    icloud_absent: bool = False


def _fantome_icloud(chemin: Path) -> bool:
    """Détecte un fichier iCloud non rapatrié."""
    nom = chemin.name
    if nom.startswith(".") and nom.endswith(".icloud"):
        return True
    # Fichier fantôme homonyme : « Livre.pdf » listé, « .Livre.pdf.icloud » présent.
    return chemin.with_name(f".{nom}.icloud").exists()


def _nom_reel(chemin: Path) -> str:
    """Nom d'origine d'un fichier fantôme (« .Livre.pdf.icloud » → « Livre.pdf »)."""
    nom = chemin.name
    if nom.startswith(".") and nom.endswith(".icloud"):
        return nom[1:-7]
    return nom


def parcourir(
    racine: str | Path,
    extensions: set[str] | None = None,
    taille_max_mo: int = 512,
) -> Iterator[FichierDecouvert]:
    """Parcourt récursivement un dossier et produit les fichiers exploitables.

    Générateur : le scan d'une bibliothèque de 50 000 ouvrages commence à
    produire des résultats immédiatement, sans construire de liste complète
    en mémoire.

    ``os.walk`` plutôt que ``Path.rglob`` : il permet d'élaguer les dossiers
    ignorés EN PLACE (via ``dirs[:]``), donc de ne jamais descendre dans un
    ``node_modules`` ou un dossier de corbeille.
    """
    racine = Path(racine).expanduser()
    if not racine.exists():
        raise FileNotFoundError(f"Chemin introuvable : {racine}")

    taille_max = taille_max_mo * 1024 * 1024

    for dossier, sous_dossiers, fichiers in os.walk(racine, followlinks=False):
        sous_dossiers[:] = [d for d in sous_dossiers if d not in DOSSIERS_IGNORES and not d.startswith(".")]
        base = Path(dossier)

        for nom in fichiers:
            chemin = base / nom
            nom_reel = _nom_reel(chemin)
            extension = Path(nom_reel).suffix.lower()

            type_doc = type_document(Path(nom_reel))
            if type_doc is None:
                continue
            if extensions and extension not in extensions:
                continue

            try:
                stat = chemin.stat()
            except OSError as exc:
                log.warning("fichier_inaccessible", path=str(chemin), error=str(exc))
                continue

            absent = _fantome_icloud(chemin)

            if not absent and stat.st_size == 0:
                # Fichier réellement vide : rien à extraire, et le signaler
                # comme une erreur polluerait le rapport d'ingestion.
                continue

            if not absent and stat.st_size > taille_max:
                # Un fichier hors norme est écarté explicitement : il ferait
                # exploser la durée d'extraction et la mémoire, et mérite un
                # traitement manuel.
                log.warning("fichier_trop_volumineux", path=str(chemin), size=stat.st_size)
                continue

            chemin_reel = chemin if not chemin.name.startswith(".") else chemin.with_name(nom_reel)
            yield FichierDecouvert(
                chemin=chemin_reel,
                chemin_relatif=str(chemin_reel.relative_to(racine)),
                taille=stat.st_size,
                mtime=stat.st_mtime,
                document_type=type_doc,
                icloud_absent=absent,
            )
