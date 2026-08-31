"""Fabriques de sessions SQLAlchemy.

Deux moteurs coexistent, pour deux régimes de travail différents :

* **asynchrone** (asyncpg) pour le bot : chaque message déclenche quelques
  requêtes courtes, et bloquer la boucle bloquerait tous les utilisateurs ;
* **synchrone** (psycopg) pour l'ingestion et Alembic : un traitement
  séquentiel long, où l'asynchrone n'apporterait aucun parallélisme réel
  mais imposerait ``await`` partout.

``pool_pre_ping`` est activé sur les deux : une connexion coupée par un
redémarrage de PostgreSQL ou un pare-feu est détectée et remplacée, au lieu
de faire échouer la première requête après la coupure.
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings

_moteur_async = None
_session_async = None


def init_async_engine(settings: Settings):
    """Crée le moteur asynchrone (une seule fois)."""
    global _moteur_async, _session_async
    if _moteur_async is None:
        _moteur_async = create_async_engine(
            settings.database_url,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            # Recyclage horaire : de nombreux hébergeurs coupent les
            # connexions inactives sans prévenir.
            pool_recycle=3600,
        )
        _session_async = async_sessionmaker(
            _moteur_async,
            class_=AsyncSession,
            expire_on_commit=False,  # les objets restent lisibles après commit
        )
    return _moteur_async


@asynccontextmanager
async def session_async() -> AsyncIterator[AsyncSession]:
    """Session asynchrone à portée de bloc, avec commit/rollback automatiques."""
    if _session_async is None:
        raise RuntimeError("init_async_engine n'a pas été appelé (voir app/main.py).")
    async with _session_async() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def fermer_async_engine() -> None:
    global _moteur_async, _session_async
    if _moteur_async is not None:
        await _moteur_async.dispose()
        _moteur_async = None
        _session_async = None


def creer_moteur_sync(settings: Settings):
    """Moteur synchrone pour les scripts. Non mis en cache : un script a une
    durée de vie courte et connue, et ferme son moteur explicitement."""
    return create_engine(
        settings.database_url_sync,
        echo=settings.DB_ECHO,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        future=True,
    )


@contextmanager
def session_sync(moteur) -> Iterator[Session]:
    fabrique = sessionmaker(moteur, class_=Session, expire_on_commit=False)
    with fabrique() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
