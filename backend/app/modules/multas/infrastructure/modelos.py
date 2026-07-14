"""Modelo ORM de multas (migración 003, doc 04 §3.8)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import ModeloTenant

_ESTADO_MULTA = "'IMPUESTA','PAGADA','ANULADA'"


class MultaModel(ModeloTenant):
    __tablename__ = "multas"
    __table_args__ = (
        CheckConstraint(f"estado IN ({_ESTADO_MULTA})", name="chk_estado_multa"),
    )

    participante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=False, index=True
    )
    catalogo_multa_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("catalogo_multas.id"), nullable=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    origen_tipo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    origen_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="IMPUESTA")
    pagada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asiento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("asientos.id"), nullable=True
    )
    anulada_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )
    justificacion_anulacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
