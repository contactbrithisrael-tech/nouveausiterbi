#!/usr/bin/env python3
"""Reconstruction de l'index vectoriel.

    python scripts/reindex.py --full      # supprime la collection et reconstruit
    python scripts/reindex.py --dry-run   # montre ce qui serait fait

Quand l'utiliser
----------------
Une seule situation l'impose réellement : le changement de modèle
d'embeddings. Les vecteurs d'un modèle ne sont pas comparables à ceux d'un
autre ; conserver l'ancien index produirait des résultats silencieusement
faux — le pire des symptômes, puisque rien n'échoue.

La suppression de la collection est demandée explicitement (``--full``) et
confirmée : c'est une opération destructrice et longue à réparer.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qdrant_client import QdrantClient  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database.models import Document, StatutDocument  # noqa: E402
from app.database.session import creer_moteur_sync, session_sync  # noqa: E402
from app.embeddings.base import get_embedding_provider  # noqa: E402
from app.utils.logging import configure_logging, get_logger  # noqa: E402
from app.vectorstore.qdrant import assurer_collection  # noqa: E402

log = get_logger("reindex")


def main() -> int:
    parseur = argparse.ArgumentParser(description="Reconstruction de l'index Joshua")
    parseur.add_argument("--full", action="store_true", help="supprime la collection Qdrant")
    parseur.add_argument("--dry-run", action="store_true", help="n'effectue aucune modification")
    parseur.add_argument("--yes", action="store_true", help="ne pas demander confirmation")
    arguments = parseur.parse_args()

    settings = get_settings()
    configure_logging(settings.LOG_LEVEL, json_output=False)
    provider = get_embedding_provider(settings)

    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=60)
    collections = {c.name for c in client.get_collections().collections}
    existe = settings.QDRANT_COLLECTION in collections
    points = client.count(settings.QDRANT_COLLECTION, exact=True).count if existe else 0

    plan = {
        "collection": settings.QDRANT_COLLECTION,
        "existe": existe,
        "points_actuels": points,
        "modele": provider.model_id,
        "dimension": provider.dimension,
        "action": "supprimer_et_recreer" if arguments.full else "creer_si_absente",
    }

    if arguments.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, **plan}, ensure_ascii=False, indent=2))
        return 0

    if arguments.full:
        if not arguments.yes:
            # La confirmation lit stdin : en environnement non interactif
            # (cron, CI), l'absence de réponse annule l'opération — c'est le
            # comportement sûr par défaut pour une action destructrice.
            reponse = input(f"Supprimer {points} points de « {settings.QDRANT_COLLECTION} » ? [oui/N] ")
            if reponse.strip().lower() not in {"oui", "o", "yes", "y"}:
                print(json.dumps({"ok": False, "annule": True}, ensure_ascii=False))
                return 1
        if existe:
            client.delete_collection(settings.QDRANT_COLLECTION)
            log.info("collection_supprimee", collection=settings.QDRANT_COLLECTION)

        # Les documents repassent en attente : le prochain passage de
        # scripts/index_library.py les réindexera tous, l'empreinte n'étant
        # plus une raison de les ignorer.
        moteur = creer_moteur_sync(settings)
        try:
            with session_sync(moteur) as session:
                session.query(Document).update({Document.status: StatutDocument.EN_ATTENTE, Document.chunk_count: 0})
        finally:
            moteur.dispose()

    assurer_collection(settings, provider.dimension)
    client.close()

    print(
        json.dumps(
            {
                "ok": True,
                **plan,
                "suite": "python scripts/index_library.py --full",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
