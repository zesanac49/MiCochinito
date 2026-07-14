"""Modelos ORM de actividades (migración 004, doc 04 §3.7)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import (
    MixinIdentidad,
    MixinTenant,
    ModeloBase,
    ModeloTenant,
)

_TIPO = "'POLLA','RIFA','BINGO','BAZAR','VENTA','OTRO','DONACION'"
_ESTADO = "'BORRADOR','ABIERTA','SORTEADA','CERRADA'"
_TIPO_MOV = "'INGRESO','GASTO','PREMIO'"


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class ActividadModel(ModeloTenant):
    __tablename__ = "actividades"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_TIPO})", name="chk_tipo_actividad"),
        CheckConstraint(f"estado IN ({_ESTADO})", name="chk_estado_actividad"),
    )

    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    periodo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("periodos.id"), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="BORRADOR")
    valor_numero: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    cantidad_numeros: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    premio: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    fecha_sorteo: Mapped[date | None] = mapped_column(Date, nullable=True)
    clonada_de_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("actividades.id"), nullable=True
    )
    utilidad_cierre: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)


class ActividadNumeroModel(ModeloTenant):
    __tablename__ = "actividad_numeros"
    __table_args__ = (
        UniqueConstraint("actividad_id", "numero", name="uq_actividad_numero"),
    )

    actividad_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actividades.id"), nullable=False, index=True
    )
    numero: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    participante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=False
    )
    pagado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pagado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActividadMovimientoModel(ModeloTenant):
    __tablename__ = "actividad_movimientos"
    __table_args__ = (
        CheckConstraint(f"tipo IN ({_TIPO_MOV})", name="chk_tipo_movimiento"),
    )

    actividad_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actividades.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    concepto: Mapped[str] = mapped_column(String(120), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    participante_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=True
    )


class SorteoModel(MixinIdentidad, MixinTenant, ModeloBase):
    """Resultado del sorteo. Inmutable (trigger MySQL como el ledger, RF-505)."""

    __tablename__ = "sorteos"
    __table_args__ = (UniqueConstraint("actividad_id", name="uq_sorteo_actividad"),)

    actividad_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("actividades.id"), nullable=False
    )
    numero_ganador: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hubo_ganador: Mapped[bool] = mapped_column(Boolean, nullable=False)
    participante_ganador_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=True
    )
    fuente: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
