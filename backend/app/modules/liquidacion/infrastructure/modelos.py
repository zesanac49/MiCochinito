"""Modelos ORM de liquidación (migración 005, doc 04 §3.9)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import MixinIdentidad, MixinTenant, ModeloBase, ModeloTenant

_FASES = "'PRE_VALIDACION','CALCULADA','EN_REVISION','CONFIRMADA','ACTA_GENERADA'"


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class LiquidacionModel(ModeloTenant):
    __tablename__ = "liquidaciones"
    __table_args__ = (
        UniqueConstraint("natillera_id", name="uq_liquidacion_natillera"),
        CheckConstraint(f"estado IN ({_FASES})", name="chk_fase_liquidacion"),
    )

    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="PRE_VALIDACION")
    estrategia_aplicada: Mapped[str | None] = mapped_column(String(30), nullable=True)
    saldo_rentabilidad_distribuido: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False, default=0
    )
    confirmada_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )
    confirmada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LiquidacionDetalleModel(ModeloTenant):
    __tablename__ = "liquidacion_detalles"
    __table_args__ = (
        CheckConstraint(
            "saldo_final = ahorros + participacion_rentabilidad - capital_pendiente "
            "- intereses_pendientes - multas_pendientes",
            name="chk_saldo_final",
        ),
    )

    liquidacion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("liquidaciones.id"), nullable=False, index=True
    )
    participante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=False
    )
    ahorros: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    participacion_rentabilidad: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    capital_pendiente: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    intereses_pendientes: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    multas_pendientes: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    saldo_final: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    entregado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    entregado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entregado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id"), nullable=True
    )


class LiquidacionDecisionModel(MixinIdentidad, MixinTenant, ModeloBase):
    """Decisión sobre un bloqueo de pre-validación (RF-702). Append-only."""

    __tablename__ = "liquidacion_decisiones"

    liquidacion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("liquidaciones.id"), nullable=False, index=True
    )
    tipo_bloqueo: Mapped[str] = mapped_column(String(40), nullable=False)
    origen_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    origen_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    decision: Mapped[str] = mapped_column(String(255), nullable=False)
    detalle: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    decidido_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
