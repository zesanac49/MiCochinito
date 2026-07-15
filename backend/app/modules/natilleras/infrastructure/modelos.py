"""Modelos ORM del módulo natilleras (migración 001, doc 04 §3.1).

Tablas: natilleras (tenant raíz), configuraciones (1:1), configuraciones_historial,
catalogo_multas, feature_flags. Los modelos NO son las entidades de dominio: hay
mappers explícitos (doc 05 §2).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import (
    MixinIdentidad,
    MixinTimestamps,
    ModeloBase,
    ModeloTenant,
)

_ESTADOS = "'BORRADOR','ABIERTA','EN_OPERACION','PENDIENTE_LIQUIDACION','LIQUIDADA','ARCHIVADA'"
_PERIODICIDAD = "'MENSUAL','QUINCENAL','SEMANAL'"
_ESTRATEGIA = "'PARTES_IGUALES','PROPORCIONAL_AHORRO','PROPORCIONAL_TIEMPO'"
_TIPO_MULTA = "'MORA_CUOTA','MORA_PRESTAMO','MORA_ACTIVIDAD','OTRA'"


class NatilleraModel(MixinIdentidad, MixinTimestamps, ModeloBase):
    """La natillera es el tenant: no lleva natillera_id (doc 04 §1)."""

    __tablename__ = "natilleras"
    __table_args__ = (CheckConstraint(f"estado IN ({_ESTADOS})", name="chk_estado_natillera"),)

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="BORRADOR")
    ciclo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    ciclo_fin: Mapped[date] = mapped_column(Date, nullable=False)


class ConfiguracionModel(ModeloTenant):
    __tablename__ = "configuraciones"
    __table_args__ = (
        UniqueConstraint("natillera_id", name="uq_config_natillera"),
        CheckConstraint(f"periodicidad_cuota IN ({_PERIODICIDAD})", name="chk_periodicidad"),
        CheckConstraint(f"estrategia_distribucion IN ({_ESTRATEGIA})", name="chk_estrategia"),
    )

    valor_cuota: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    periodicidad_cuota: Mapped[str] = mapped_column(String(30), nullable=False)
    dia_limite_pago: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    permite_aportes_extra: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tasa_interes_base: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    tasa_interes_min: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    tasa_interes_max: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    max_prestamos_activos: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    max_capital_vigente: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    estrategia_distribucion: Mapped[str] = mapped_column(String(30), nullable=False)
    estrategia_congelada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Mora fija por semana de atraso de una cuota de ahorro (RF, 3B).
    valor_mora: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)


class ConfiguracionHistorialModel(ModeloTenant):
    """Snapshot de configuración para auditar "qué regla regía cuándo" (RN-020)."""

    __tablename__ = "configuraciones_historial"

    snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    autor_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)


class CatalogoMultaModel(ModeloTenant):
    __tablename__ = "catalogo_multas"
    __table_args__ = (CheckConstraint(f"tipo IN ({_TIPO_MULTA})", name="chk_tipo_multa"),)

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FeatureFlagModel(ModeloTenant):
    __tablename__ = "feature_flags"
    __table_args__ = (UniqueConstraint("natillera_id", "flag", name="uq_flag_natillera"),)

    flag: Mapped[str] = mapped_column(String(50), nullable=False)
    habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
