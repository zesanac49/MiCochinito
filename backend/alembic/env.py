"""Entorno de migraciones Alembic (TEC-09, doc 04 §6).

- La URL de conexión se toma de `DATABASE_URL` (nunca hardcodeada).
- `target_metadata` apunta a `ModeloBase.metadata`; a medida que cada módulo
  define sus modelos ORM, se importan aquí para que autogenerate los vea.
- Ninguna migración debe ejecutar UPDATE/DELETE sobre el ledger (doc 04 §6);
  esa regla se vigila en la revisión de cada migración, no automáticamente.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.shared.infrastructure.db import ModeloBase
from app.shared.infrastructure import todos_los_modelos  # noqa: F401  (puebla metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# La URL efectiva viene de Settings (env). Sobrescribe el marcador del .ini.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Metadata objetivo: la poblan los imports de `todos_los_modelos`.
target_metadata = ModeloBase.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
