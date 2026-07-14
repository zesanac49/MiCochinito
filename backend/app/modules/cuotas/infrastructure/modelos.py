"""Modelo ORM de cuotas (migración 002, doc 04 §3.5).

`UNIQUE(natillera_id, participante_id, periodo_id)` es la idempotencia de RF-301
como constraint: un período pagado no admite doble registro sin reversión previa.
"""

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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import ModeloTenant

_ESTADO_CUOTA = "'PENDIENTE','PAGADA','REVERTIDA'"


class CuotaModel(ModeloTenant):
    __tablename__ = "cuotas"
    __table_args__ = (
        UniqueConstraint(
            "natillera_id", "participante_id", "periodo_id", name="uq_cuota_periodo"
        ),
        CheckConstraint(f"estado IN ({_ESTADO_CUOTA})", name="chk_estado_cuota"),
    )

    participante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=False
    )
    periodo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("periodos.id"), nullable=False
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="PAGADA")
    pagada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    asiento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("asientos.id"), nullable=True
    )
