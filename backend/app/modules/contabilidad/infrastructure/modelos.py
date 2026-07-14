"""Modelos ORM del núcleo contable (migración 001, doc 04 §3.4).

`AsientoModel` es EL LEDGER: inmutable (sin `updated_at`) con CHECKs de
naturaleza/concepto/monto>0 (capa 2 de la defensa en 3 capas, doc 04 §4). Las
listas de los CHECK se generan desde los enums de dominio para evitar
divergencia. Los triggers de inmutabilidad (capa 3, MySQL) van en la migración.
"""

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

from app.modules.contabilidad.domain.conceptos import ConceptoContable, Naturaleza
from app.shared.infrastructure.db import (
    MixinIdentidad,
    MixinTenant,
    ModeloBase,
    ModeloTenant,
)


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


def _sql_in(valores: list[str]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


_CONCEPTOS = _sql_in([c.value for c in ConceptoContable])
_NATURALEZAS = _sql_in([n.value for n in Naturaleza])
_TIPO_FONDO = "'AHORRO','RENTABILIDAD'"
_ORIGEN = _sql_in(
    [
        "CUOTA", "PRESTAMO", "PAGO_PRESTAMO", "ACTIVIDAD", "MULTA",
        "LIQUIDACION", "REVERSION", "APORTE_EXTRAORDINARIO",
    ]
)


class FondoModel(ModeloTenant):
    __tablename__ = "fondos"
    __table_args__ = (
        UniqueConstraint("natillera_id", "tipo", name="uq_fondo_tipo"),
        CheckConstraint(f"tipo IN ({_TIPO_FONDO})", name="chk_tipo_fondo"),
    )

    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    saldo_cache: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    saldo_cache_actualizado: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PeriodoModel(ModeloTenant):
    __tablename__ = "periodos"
    __table_args__ = (UniqueConstraint("natillera_id", "anio", "mes", name="uq_periodo"),)

    anio: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fecha_limite_cuota: Mapped[date | None] = mapped_column(Date, nullable=True)
    conciliado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AsientoModel(MixinIdentidad, MixinTenant, ModeloBase):
    """EL LEDGER. Inmutable: solo created_at, sin updated_at (RN-060, INV-11)."""

    __tablename__ = "asientos"
    __table_args__ = (
        CheckConstraint(f"naturaleza IN ({_NATURALEZAS})", name="chk_naturaleza"),
        CheckConstraint("monto > 0", name="chk_monto_positivo"),
        CheckConstraint(f"concepto IN ({_CONCEPTOS})", name="chk_concepto"),
        CheckConstraint(f"origen_tipo IN ({_ORIGEN})", name="chk_origen_tipo"),
    )

    fondo_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fondos.id"), nullable=False)
    participante_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=True
    )
    naturaleza: Mapped[str] = mapped_column(String(10), nullable=False)
    concepto: Mapped[str] = mapped_column(String(40), nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    periodo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("periodos.id"), nullable=True
    )
    origen_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    origen_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reversa_de_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("asientos.id"), nullable=True
    )
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    creado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
