"""Environnement Alembic.

Deux points méritent une explication :

* **L'URL vient de ``Settings``**, jamais d'``alembic.ini`` : le mot de passe
  PostgreSQL ne doit exister qu'à un seul endroit, le ``.env``, qui n'est pas
  versionné.

* **Le pilote est synchrone (psycopg)**, alors que l'application utilise
  asyncpg. Une migration est une opération séquentielle et transactionnelle ;
  l'asynchrone n'y apporte rien et complique la gestion des erreurs.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.database.models import Base  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url_sync)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # une migration n'a que faire d'un pool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # compare_type : détecte un changement de type de colonne, que
            # l'autogénération ignore par défaut et qui passerait sinon
            # inaperçu jusqu'à l'erreur en production.
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
