"""Journalisation structurée.

Choix d'architecture
--------------------
* **structlog en sortie JSON par défaut.** Les logs de ce service seront lus
  par une machine (agrégateur, ``docker logs | jq``) bien avant d'être lus par
  un humain. Le rendu console coloré reste disponible via ``LOG_JSON=false``
  pour le développement.

* **Contexte porté par ``contextvars``.** ``telegram_user_id`` et
  ``request_id`` sont liés une fois, à l'entrée du traitement d'un message,
  puis apparaissent automatiquement dans TOUTES les lignes émises ensuite,
  y compris au fond de la pile RAG. L'alternative — passer ces valeurs de
  fonction en fonction — polluerait chaque signature du projet.

* **Aucune donnée personnelle dans les logs par défaut.** On journalise
  l'identifiant Telegram (nécessaire au support) mais jamais le contenu des
  messages : ce sont des conversations privées.
"""

from __future__ import annotations

import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import structlog

_CONFIGURED = False


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog et la stdlib. Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    niveau = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=niveau)

    # Les bibliothèques tierces sont bruyantes au niveau INFO ; on les
    # remonte à WARNING pour que les logs de Joshua restent lisibles.
    for bruyant in ("httpx", "httpcore", "urllib3", "telegram.ext", "asyncio"):
        logging.getLogger(bruyant).setLevel(logging.WARNING)

    processeurs: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.CallsiteParameterAdder(
            {structlog.processors.CallsiteParameter.MODULE}
        ),
    ]
    if json_output:
        processeurs += [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    else:
        processeurs += [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processeurs,
        wrapper_class=structlog.make_filtering_bound_logger(niveau),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(nom: str) -> Any:
    """Logger nommé. ``configure_logging`` est appelée si elle ne l'a pas été.

    Cette garde évite le piège classique du logger silencieux : un module
    importé avant l'initialisation de l'application émettrait sinon dans le
    vide, et l'erreur ne se voit qu'en production.
    """
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(nom)


def bind_request(telegram_user_id: int | None = None, request_id: str | None = None) -> str:
    """Attache l'identité de la requête courante au contexte de journalisation."""
    rid = request_id or uuid.uuid4().hex[:12]
    structlog.contextvars.bind_contextvars(request_id=rid)
    if telegram_user_id is not None:
        structlog.contextvars.bind_contextvars(telegram_user_id=telegram_user_id)
    return rid


def clear_request() -> None:
    """À appeler en fin de traitement.

    Sans cela, le contexte d'un utilisateur fuirait sur le message suivant :
    les contextvars survivent à la tâche asyncio dans un pool réutilisé.
    """
    structlog.contextvars.clear_contextvars()


@contextmanager
def timed(logger: Any, evenement: str, **champs: Any) -> Iterator[dict[str, Any]]:
    """Mesure une durée et l'émet, même en cas d'exception.

    La durée d'une opération ratée est au moins aussi instructive que celle
    d'une opération réussie (distinguer un échec immédiat d'un timeout).
    """
    debut = time.perf_counter()
    extra: dict[str, Any] = {}
    try:
        yield extra
    except Exception as exc:
        logger.error(
            evenement,
            duration_ms=round((time.perf_counter() - debut) * 1000, 2),
            error=type(exc).__name__,
            **champs,
            **extra,
        )
        raise
    else:
        logger.info(
            evenement,
            duration_ms=round((time.perf_counter() - debut) * 1000, 2),
            **champs,
            **extra,
        )
