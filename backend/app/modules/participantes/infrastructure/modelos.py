"""Modelo ORM de participantes (migración 001, doc 04 §3.3)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import ModeloTenant

_TIPO_DOC = "'CC','CE','TI','PP'"
_ESTADO_PART = "'ACTIVO','SUSPENDIDO','RETIRADO'"


class ParticipanteModel(ModeloTenant):
    __tablename__ = "participantes"
    __table_args__ = (
        UniqueConstraint(
            "natillera_id", "tipo_documento", "numero_documento", name="uq_participante_doc"
        ),
        CheckConstraint(f"tipo_documento IN ({_TIPO_DOC})", name="chk_tipo_doc"),
        CheckConstraint(f"estado IN ({_ESTADO_PART})", name="chk_estado_participante"),
    )

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_documento: Mapped[str] = mapped_column(String(4), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(30), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVO")
    fecha_ingreso: Mapped[date] = mapped_column(Date, nullable=False)
    # Cuota mensual propia (RF-301). NULL => se usa el default de la configuración.
    valor_cuota: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
