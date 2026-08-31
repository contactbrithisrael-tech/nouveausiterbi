#!/usr/bin/env python3
"""Import du corpus documentaire du Rite Brith Israël.

    python scripts/import_rbi.py --dry-run   # que va-t-il être importé ?
    python scripts/import_rbi.py             # importe le corpus RBI
    python scripts/import_rbi.py --library   # + la bibliothèque personnelle

Pourquoi un script dédié plutôt que « ingest.py --category rbi »
----------------------------------------------------------------
Deux raisons, et aucune n'est cosmétique :

1. **Les conventions du corpus sont encodées ici, une fois pour toutes.**
   Catégorie, étiquettes et nom de source déterminent les filtres Qdrant
   disponibles au moment de répondre. Les retaper à la main à chaque import
   garantit qu'ils finiront par diverger — et un corpus dont la moitié porte
   « rbi » et l'autre « RBI » n'est plus filtrable.

2. **Les documents ne vivent pas dans le projet.** Ils sont à la racine du
   dépôt du site, d'où ils sont publiés. Les copier dans `data/incoming/`
   créerait une seconde copie de 19 Mo, qui divergerait de l'originale à la
   première mise à jour. Le script va donc les CHERCHER là où ils sont.

Ordre de recherche des sources
------------------------------
1. l'argument ``--source`` ;
2. la variable d'environnement ``JOSHUA_RBI_SOURCE`` ;
3. ``data/incoming/rbi/`` (dépôt manuel) ;
4. la racine du dépôt parent — emplacement réel des documents publiés.

Les originaux ne sont jamais modifiés, déplacés ni renommés.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.database.repository import cloturer_job, creer_job  # noqa: E402
from app.database.session import creer_moteur_sync, session_sync  # noqa: E402
from app.embeddings.base import get_embedding_provider  # noqa: E402
from app.ingestion.loader import parcourir  # noqa: E402
from app.ingestion.pipeline import Compteurs, ingerer  # noqa: E402
from app.utils.logging import configure_logging, get_logger  # noqa: E402

log = get_logger("import_rbi")

RACINE_PROJET = Path(__file__).resolve().parents[1]

#: Conventions du corpus. Elles pilotent les filtres Qdrant : une question
#: pourra être restreinte à `category=rbi` sans dépendre du nom des fichiers.
CATEGORIE = "rbi"
SOURCE = "rbi_officiel"
TAGS = ["rbi", "officiel"]

#: Formats admis quand la source est le dépôt du site (repli n° 4). Un dépôt
#: contient des .json, des .txt et des .md qui sont du CODE et de la
#: configuration, pas des documents : les indexer noierait le corpus sous des
#: fragments de package.json. Un dossier désigné explicitement, lui, n'est pas
#: restreint — l'utilisateur sait ce qu'il y a mis.
EXTENSIONS_DEPOT = {".pdf", ".epub", ".docx"}


def localiser_sources(explicite: str | None) -> list[Path]:
    """Retourne les dossiers à parcourir, dans l'ordre de priorité.

    Le premier emplacement contenant au moins un document gagne. On ne
    cumule pas les emplacements : ingérer deux fois les mêmes fichiers
    depuis deux chemins différents produirait des doublons de chemins dans
    le catalogue (la déduplication par empreinte les rattraperait, mais le
    rapport serait trompeur).
    """
    candidats: list[Path] = []
    if explicite:
        candidats.append(Path(explicite).expanduser())
    if os.environ.get("JOSHUA_RBI_SOURCE"):
        candidats.append(Path(os.environ["JOSHUA_RBI_SOURCE"]).expanduser())
    candidats.append(RACINE_PROJET / "data" / "incoming" / "rbi")
    candidats.append(RACINE_PROJET.parent)  # dépôt du site : PDF publiés

    for candidat in candidats:
        if not candidat.exists():
            continue
        if any(True for _ in _scanner(candidat)):
            return [candidat]
    return []


def regles_de_scan(dossier: Path) -> dict:
    """Règles de parcours applicables à un dossier source.

    Le dépôt du site est parcouru À PLAT et restreint aux formats
    documentaires ; un dossier dédié est parcouru récursivement et sans
    restriction. Cette distinction est la seule chose qui empêche un import
    « RBI » de se remplir de fichiers de projet.

    Les règles sont retournées sous forme de dictionnaire, et non appliquées
    ici, pour être passées À L'IDENTIQUE à l'inventaire et à l'ingestion.
    Deux chemins de code qui « filtrent pareil » finissent toujours par
    filtrer différemment.
    """
    est_depot = dossier == RACINE_PROJET.parent
    return {
        "extensions": EXTENSIONS_DEPOT if est_depot else None,
        "profondeur_max": 0 if est_depot else None,
    }


def _scanner(dossier: Path, taille_max_mo: int = 512):
    return parcourir(dossier, taille_max_mo=taille_max_mo, **regles_de_scan(dossier))


def inventaire(dossiers: list[Path], settings) -> dict:
    """Liste ce qui serait importé, sans rien ouvrir au-delà d'un ``stat``."""
    fichiers = []
    for dossier in dossiers:
        for fichier in _scanner(dossier, settings.INGEST_MAX_FILE_MB):
            fichiers.append(
                {
                    "fichier": fichier.chemin_relatif,
                    "type": fichier.document_type,
                    "taille_mo": round(fichier.taille / 1e6, 2),
                    "disponible": not fichier.icloud_absent,
                }
            )
    return {
        "sources": [str(d) for d in dossiers],
        "total": len(fichiers),
        "volume_mo": round(sum(f["taille_mo"] for f in fichiers), 2),
        "indisponibles_localement": sum(1 for f in fichiers if not f["disponible"]),
        "documents": sorted(fichiers, key=lambda f: f["fichier"]),
    }


def _barre(prefixe: str, compteurs: Compteurs) -> None:
    sys.stderr.write(
        f"\r\033[K{compteurs.vus:>4} vus | {compteurs.indexes:>4} indexés | "
        f"{compteurs.ignores:>4} inchangés | {compteurs.erreurs:>3} erreurs | "
        f"{compteurs.chunks:>6} chunks | {prefixe[-48:]}"
    )
    sys.stderr.flush()


def main() -> int:
    parseur = argparse.ArgumentParser(description="Import du corpus RBI dans Joshua")
    parseur.add_argument("--source", default=None, help="dossier des documents RBI")
    parseur.add_argument("--dry-run", action="store_true", help="inventaire seul, aucun import")
    parseur.add_argument("--full", action="store_true", help="réindexer même les documents inchangés")
    parseur.add_argument(
        "--library",
        action="store_true",
        help="importer aussi JOSHUA_LIBRARY_PATH (bibliothèque personnelle)",
    )
    arguments = parseur.parse_args()

    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=False)

    dossiers = localiser_sources(arguments.source)
    if not dossiers:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "aucun document RBI trouvé",
                    "cherché_dans": [
                        arguments.source or "(--source non fourni)",
                        os.environ.get("JOSHUA_RBI_SOURCE", "(JOSHUA_RBI_SOURCE non défini)"),
                        str(RACINE_PROJET / "data" / "incoming" / "rbi"),
                        str(RACINE_PROJET.parent),
                    ],
                    "remède": "déposer les documents dans data/incoming/rbi/ ou passer --source",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    if arguments.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **inventaire(dossiers, settings)},
                         ensure_ascii=False, indent=2))
        return 0

    provider = get_embedding_provider(settings)
    moteur = creer_moteur_sync(settings)
    debut = time.perf_counter()
    rapports = []

    try:
        with session_sync(moteur) as session:
            job = creer_job(session, ",".join(str(d) for d in dossiers), "rbi")
            erreur = None
            cumul = Compteurs()
            try:
                for dossier in dossiers:
                    sys.stderr.write(f"→ {dossier}\n")
                    compteurs = ingerer(
                        dossier,
                        settings=settings,
                        provider=provider,
                        session=session,
                        mode="full" if arguments.full else "incremental",
                        source=SOURCE,
                        categorie=CATEGORIE,
                        tags=TAGS,
                        progression=_barre,
                        # Mêmes règles que l'inventaire : ce qui a été annoncé
                        # par --dry-run est exactement ce qui est importé.
                        **regles_de_scan(dossier),
                    )
                    sys.stderr.write("\n")
                    rapports.append({"source": str(dossier), **compteurs.resume()})
                    for champ in ("vus", "indexes", "ignores", "erreurs", "icloud_absents", "chunks"):
                        setattr(cumul, champ, getattr(cumul, champ) + getattr(compteurs, champ))
                    cumul.details.extend(compteurs.details)

                if arguments.library:
                    # La bibliothèque personnelle garde SES conventions : elle
                    # n'est pas du corpus officiel, et les mélanger interdirait
                    # de restreindre une question aux textes de l'Ordre.
                    if not settings.JOSHUA_LIBRARY_PATH:
                        sys.stderr.write("⚠ JOSHUA_LIBRARY_PATH non défini : bibliothèque ignorée\n")
                    else:
                        bibliotheque = Path(settings.JOSHUA_LIBRARY_PATH).expanduser()
                        sys.stderr.write(f"→ {bibliotheque}\n")
                        compteurs = ingerer(
                            bibliotheque,
                            settings=settings,
                            provider=provider,
                            session=session,
                            mode="full" if arguments.full else "incremental",
                            source="icloud_library",
                            categorie="bibliotheque",
                            tags=["livre"],
                            progression=_barre,
                        )
                        sys.stderr.write("\n")
                        rapports.append({"source": str(bibliotheque), **compteurs.resume()})
                        for champ in ("vus", "indexes", "ignores", "erreurs", "icloud_absents", "chunks"):
                            setattr(cumul, champ, getattr(cumul, champ) + getattr(compteurs, champ))
                        cumul.details.extend(compteurs.details)
            except Exception as exc:
                erreur = f"{type(exc).__name__}: {exc}"
                log.error("import_rbi_interrompu", error=erreur, exc_info=True)
            cloturer_job(session, job, cumul.resume(), erreur)

        print(
            json.dumps(
                {
                    "ok": erreur is None,
                    "categorie": CATEGORIE,
                    "source": SOURCE,
                    "tags": TAGS,
                    "duree_s": round(time.perf_counter() - debut, 1),
                    "total": cumul.resume(),
                    "par_source": rapports,
                    "details": cumul.details[:50],
                    **({"error": erreur} if erreur else {}),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if erreur is None else 1
    finally:
        moteur.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
