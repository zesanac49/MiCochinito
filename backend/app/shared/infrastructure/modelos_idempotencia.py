"""Modelo de claves de idempotencia (migración 002, doc 07 §1).

Soporta el header `Idempotency-Key` en POST financieros: la misma clave con el
mismo payload devuelve el resultado original; con payload distinto es conflicto.
Transversal (cualquier operación financiera puede usarlo).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import MixinIdentidad, MixinTenant, ModeloBase


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class IdempotencyKeyModel(MixinIdentidad, MixinTenant, ModeloBase):
    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("natillera_id", "clave", name="uq_idempotency"),)

    clave: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_payload: Mapped[str] = mapped_column(String(64), nullable=False)
    referencia_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
