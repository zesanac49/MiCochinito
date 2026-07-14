"""Modelo ORM de auditoría de acciones (transversal, doc 04 §3.10).

Auditoría de acciones NO contables (transiciones de estado, cambios de config,
anulaciones, decisiones). Complementa al ledger: el ledger audita dinero, esta
tabla audita decisiones (RN-062, INV-13). Append-only (mismos triggers del
ledger en MySQL).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import MixinIdentidad, MixinTenant, ModeloBase


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class AuditoriaAccionModel(MixinIdentidad, MixinTenant, ModeloBase):
    __tablename__ = "auditoria_acciones"

    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad_tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    detalle: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
