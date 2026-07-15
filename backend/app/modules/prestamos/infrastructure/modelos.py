"""Modelos ORM de préstamos (migración 003, doc 04 §3.6)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import ModeloTenant

_ESTADO_PRESTAMO = (
    "'SOLICITADO','APROBADO','RECHAZADO','DESEMBOLSADO','EN_PAGO','EN_MORA','PAGADO'"
)


class PrestamoModel(ModeloTenant):
    __tablename__ = "prestamos"
    __table_args__ = (
        CheckConstraint(f"estado IN ({_ESTADO_PRESTAMO})", name="chk_estado_prestamo"),
    )

    participante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=False, index=True
    )
    capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tasa_interes: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    plazo_meses: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    fecha_desembolso: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="SOLICITADO")
    motivo_rechazo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    saldo_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    # Interés simple devengado no pagado y fecha hasta la que ya se calculó.
    interes_acumulado: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    fecha_ultimo_calculo: Mapped[date | None] = mapped_column(Date, nullable=True)


class PrestamoPagoModel(ModeloTenant):
    """Descomposición del pago y enlace a los dos asientos (RN-033)."""

    __tablename__ = "prestamo_pagos"
    __table_args__ = (
        CheckConstraint(
            "componente_capital + componente_interes = monto_recibido",
            name="chk_descomposicion",
        ),
    )

    prestamo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("prestamos.id"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto_recibido: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    componente_capital: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    componente_interes: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    asiento_capital_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("asientos.id"), nullable=True
    )
    asiento_interes_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("asientos.id"), nullable=True
    )
