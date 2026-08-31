#!/usr/bin/env python3
"""Indexation de la bibliothèque iCloud (``JOSHUA_LIBRARY_PATH``).

    python scripts/index_library.py --scan     # inventaire, n'indexe rien
    python scripts/index_library.py --update   # nouveautés et modifications
    python scripts/index_library.py --full     # reconstruction complète

Règle absolue : la bibliothèque source est en LECTURE SEULE. Ce script
n'écrit, ne renomme, ne déplace et ne supprime jamais rien dans
``JOSHUA_LIBRARY_PATH``. Les livres restent là où leur propriétaire les a
rangés ; Qdrant n'en est que l'index.

Le cas iCloud
-------------
Un fichier peut être visible dans le Finder sans être présent sur le disque.
``--scan`` les compte, ``--update`` les signale et poursuit. Aucun
rapatriement n'est déclenché : forcer le téléchargement de centaines de
gigaoctets est une décision qui appartient à l'utilisateur, pas au script.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.database.repository import cloturer_job, creer_job, index_bibliotheque  # noqa: E402
from app.database.session import creer_moteur_sync, session_sync  # noqa: E402
from app.embeddings.base import get_embedding_provider  # noqa: E402
from app.ingestion.deduplication import fichier_inchange  # noqa: E402
from app.ingestion.loader import parcourir  # noqa: E402
from app.ingestion.pipeline import Compteurs, ingerer  # noqa: E402
from app.utils.logging import configure_logging, get_logger  # noqa: E402

log = get_logger("index_library")


def inventaire(racine: Path, settings, moteur) -> dict:
    """Inventaire sans indexation : le mode ``--scan``.

    Il répond à la question posée avant tout import massif : « combien de
    temps cela va-t-il prendre, et qu'est-ce qui manque ? ». Aucun fichier
    n'est ouvert au-delà d'un ``stat`` — sauf pour vérifier une empreinte
    quand la date de modification a changé.
    """
    with session_sync(moteur) as session:
        connus = index_bibliotheque(session)

    par_type: Counter[str] = Counter()
    total = nouveaux = modifies = inchanges = absents = 0
    octets = 0

    for fichier in parcourir(racine, taille_max_mo=settings.INGEST_MAX_FILE_MB):
        total += 1
        par_type[fichier.document_type] += 1
        octets += fichier.taille
        if fichier.icloud_absent:
            absents += 1
            continue
        entree = connus.get(str(fichier.chemin))
        if entree is None:
            nouveaux += 1
        elif fichier_inchange(fichier.chemin, entree[1], entree[2]):
            inchanges += 1
        else:
            modifies += 1

    return {
        "racine": str(racine),
        "total": total,
        "par_type": dict(sorted(par_type.items())),
        "deja_indexes": inchanges,
        "nouveaux": nouveaux,
        "modifies": modifies,
        "indisponibles_localement": absents,
        "volume_go": round(octets / 1e9, 2),
    }


def _barre(prefixe: str, compteurs: Compteurs) -> None:
    sys.stderr.write(
        f"\r\033[K{compteurs.vus:>6} vus | {compteurs.indexes:>5} indexés | "
        f"{compteurs.ignores:>5} inchangés | {compteurs.icloud_absents:>4} iCloud | "
        f"{compteurs.erreurs:>4} erreurs | {compteurs.chunks:>7} chunks | {prefixe[-46:]}"
    )
    sys.stderr.flush()


def main() -> int:
    parseur = argparse.ArgumentParser(description="Indexation de la bibliothèque Joshua")
    groupe = parseur.add_mutually_exclusive_group()
    groupe.add_argument("--scan", action="store_true", help="inventaire seul, aucune indexation")
    groupe.add_argument("--update", action="store_true", help="nouveautés et modifications (défaut)")
    groupe.add_argument("--full", action="store_true", help="reconstruction complète de l'index")
    parseur.add_argument("--path", default=None, help="remplace JOSHUA_LIBRARY_PATH")
    parseur.add_argument("--category", default="bibliotheque")
    parseur.add_argument("--tags", default="livre")
    parseur.add_argument(
        "--purge-absents",
        action="store_true",
        help="retire de l'index les livres qui ne sont plus dans la bibliothèque",
    )
    arguments = parseur.parse_args()

    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=False)

    chemin = arguments.path or settings.JOSHUA_LIBRARY_PATH
    if not chemin:
        print(json.dumps({"ok": False, "error": "JOSHUA_LIBRARY_PATH non défini (voir .env)"}, ensure_ascii=False))
        return 1
    racine = Path(chemin).expanduser()
    if not racine.exists():
        print(json.dumps({"ok": False, "error": f"bibliothèque introuvable : {racine}"}, ensure_ascii=False))
        return 1

    moteur = creer_moteur_sync(settings)
    try:
        if arguments.scan:
            rapport = inventaire(racine, settings, moteur)
            print(json.dumps({"ok": True, "mode": "scan", **rapport}, ensure_ascii=False, indent=2))
            return 0

        provider = get_embedding_provider(settings)
        mode = "full" if arguments.full else "incremental"
        debut = time.perf_counter()

        with session_sync(moteur) as session:
            job = creer_job(session, str(racine), f"library:{mode}")
            erreur = None
            try:
                compteurs = ingerer(
                    racine,
                    settings=settings,
                    provider=provider,
                    session=session,
                    mode=mode,
                    source="icloud_library",
                    categorie=arguments.category,
                    tags=[t.strip() for t in arguments.tags.split(",") if t.strip()],
                    progression=_barre,
                    supprimer_absents=arguments.purge_absents,
                )
            except Exception as exc:
                erreur = f"{type(exc).__name__}: {exc}"
                compteurs = Compteurs()
                log.error("indexation_interrompue", error=erreur, exc_info=True)
            cloturer_job(session, job, compteurs.resume(), erreur)

        sys.stderr.write("\n")
        print(
            json.dumps(
                {
                    "ok": erreur is None,
                    "mode": mode,
                    "racine": str(racine),
                    "duree_s": round(time.perf_counter() - debut, 1),
                    **compteurs.resume(),
                    "details": compteurs.details[:50],
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
