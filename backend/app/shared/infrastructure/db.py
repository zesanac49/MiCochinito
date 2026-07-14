"""Base ORM, mixins y fábrica de sesiones/engine (doc 04 §1, doc 05 §11).

- `ModeloBase`: declarative base de SQLAlchemy 2.0 (estilo `Mapped`).
- `MixinIdentidad`: PK BIGINT interna + `uuid` público (ADR-06, doc 04 §1).
- `MixinTenant`: `natillera_id` obligatorio (TEC-02).
- `MixinTimestamps`: created_at/updated_at UTC.
- `crear_engine` / `crear_session_factory`: infraestructura de conexión.

Nota: los modelos concretos de cada módulo llegan en Sprints 1+. Aquí solo se
define la base común para que el repositorio con tenant y el UoW existan.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Engine, Integer, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from app.core.config import Settings


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


# BIGINT en prod (MySQL); INTEGER en SQLite para que autoincremente en tests.
_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ModeloBase(DeclarativeBase):
    """Base declarativa de todos los modelos ORM."""


class MixinIdentidad:
    """PK interna BIGINT + uuid público (nunca se exponen ids numéricos)."""

    id: Mapped[int] = mapped_column(_PK_TYPE, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )


class MixinTenant:
    """Aislamiento multi-tenant obligatorio (TEC-02)."""

    natillera_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class MixinTimestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )


class ModeloTenant(MixinIdentidad, MixinTenant, MixinTimestamps, ModeloBase):
    """Base para modelos de negocio multi-tenant: aporta id/uuid, natillera_id
    y timestamps. El repositorio con tenant se tipa contra esta base, por lo que
    `natillera_id` y `uuid` son atributos conocidos (sin type: ignore)."""

    __abstract__ = True


def crear_engine(settings: Settings) -> Engine:
    """Crea el engine. SQLite en local/tests; MySQL en integración/prod."""
    if settings.usa_sqlite:
        # check_same_thread=False para TestClient; SQLite no usa pool dimensionado.
        return create_engine(
            settings.database_url,
            echo=settings.db_echo,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
