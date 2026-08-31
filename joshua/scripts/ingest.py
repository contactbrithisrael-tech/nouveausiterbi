#!/usr/bin/env python3
"""Ingestion d'un dossier de documents (par défaut ``data/incoming/``).

    python scripts/ingest.py data/incoming/
    python scripts/ingest.py data/incoming/ --category reglements --tags interne,2026
    python scripts/ingest.py data/incoming/ --full

Ce script est SYNCHRONE et volontairement. L'ingestion est une longue suite
d'opérations dépendantes (lire → extraire → encoder → écrire) : l'asynchrone
n'y apporterait aucun parallélisme réel, seulement de la complexité. Le
parallélisme utile est ailleurs — dans les lots d'encodage, gérés par le
pipeline.

La progression est affichée sur stderr ; stdout reçoit un rapport JSON final,
directement exploitable par un ordonnanceur ou un script de supervision.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Le script est exécutable depuis la racine du projet sans installation :
# c'est la première chose que fait un utilisateur, avant tout `pip install -e`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.database.repository import cloturer_job, creer_job  # noqa: E402
from app.database.session import creer_moteur_sync, session_sync  # noqa: E402
from app.embeddings.base import get_embedding_provider  # noqa: E402
from app.ingestion.pipeline import Compteurs, ingerer  # noqa: E402
from app.utils.logging import configure_logging, get_logger  # noqa: E402

log = get_logger("ingest")


def _barre(prefixe: str, compteurs: Compteurs) -> None:
    """Progression sur une seule ligne, réécrite en place.

    Sur stderr : stdout est réservé au rapport JSON, afin que
    ``python scripts/ingest.py … > rapport.json`` reste exploitable.
    """
    nom = prefixe[-52:]
    sys.stderr.write(
        f"\r\033[K{compteurs.vus:>6} vus | {compteurs.indexes:>5} indexés | "
        f"{compteurs.ignores:>5} ignorés | {compteurs.erreurs:>4} erreurs | "
        f"{compteurs.chunks:>7} chunks | {nom}"
    )
    sys.stderr.flush()


def main() -> int:
    parseur = argparse.ArgumentParser(description="Ingestion documentaire Joshua")
    parseur.add_argument("chemin", nargs="?", default="data/incoming", help="dossier à ingérer")
    parseur.add_argument("--full", action="store_true", help="tout réindexer, sans déduplication de fichiers")
    parseur.add_argument("--category", default=None, help="catégorie appliquée à tous les documents")
    parseur.add_argument("--tags", default="", help="étiquettes séparées par des virgules")
    parseur.add_argument("--source", default="incoming", help="nom logique de la source")
    arguments = parseur.parse_args()

    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=False)

    racine = Path(arguments.chemin).expanduser()
    if not racine.exists():
        print(json.dumps({"ok": False, "error": f"chemin introuvable : {racine}"}, ensure_ascii=False))
        return 1

    provider = get_embedding_provider(settings)
    moteur = creer_moteur_sync(settings)
    tags = [t.strip() for t in arguments.tags.split(",") if t.strip()]
    debut = time.perf_counter()

    try:
        with session_sync(moteur) as session:
            job = creer_job(session, str(racine), "full" if arguments.full else "incremental")
            erreur = None
            try:
                compteurs = ingerer(
                    racine,
                    settings=settings,
                    provider=provider,
                    session=session,
                    mode="full" if arguments.full else "incremental",
                    source=arguments.source,
                    categorie=arguments.category,
                    tags=tags,
                    progression=_barre,
                )
            except Exception as exc:
                erreur = f"{type(exc).__name__}: {exc}"
                compteurs = Compteurs()
                log.error("ingestion_interrompue", error=erreur, exc_info=True)
            cloturer_job(session, job, compteurs.resume(), erreur)

        sys.stderr.write("\n")
        rapport = {
            "ok": erreur is None,
            "job_id": job.id,
            "duree_s": round(time.perf_counter() - debut, 1),
            **compteurs.resume(),
            # Les détails sont bornés : un import de 40 000 fichiers dont
            # 5 000 en erreur produirait sinon un rapport illisible.
            "details": compteurs.details[:50],
        }
        if erreur:
            rapport["error"] = erreur
        print(json.dumps(rapport, ensure_ascii=False, indent=2))
        return 0 if erreur is None else 1
    finally:
        moteur.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
