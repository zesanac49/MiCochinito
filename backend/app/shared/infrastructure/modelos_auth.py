"""Modelos ORM de identidad y acceso (migración 001, doc 04 §3.2).

Identidad es transversal (no pertenece a un módulo de negocio): usuarios es
global; la membresía usuario-natillera porta el rol y, si es CLIENTE, el
participante vinculado. Refresh tokens soportan rotación/revocación (RF-1001).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db import MixinIdentidad, MixinTimestamps, ModeloBase

_ROLES = "'ADMINISTRADOR','SUPERVISOR','CLIENTE'"


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class UsuarioModel(MixinIdentidad, MixinTimestamps, ModeloBase):
    __tablename__ = "usuarios"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hash_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UsuarioNatilleraModel(MixinIdentidad, MixinTimestamps, ModeloBase):
    """Membresía usuario↔natillera con rol (doc 04 §3.2). participante_id es
    obligatorio si rol=CLIENTE (validado en dominio/servicio)."""

    __tablename__ = "usuarios_natilleras"
    __table_args__ = (
        UniqueConstraint("usuario_id", "natillera_id", name="uq_membresia"),
        CheckConstraint(f"rol IN ({_ROLES})", name="chk_rol"),
    )

    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    natillera_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("natilleras.id"), nullable=False, index=True
    )
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    participante_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("participantes.id"), nullable=True
    )


class RefreshTokenModel(MixinIdentidad, ModeloBase):
    __tablename__ = "refresh_tokens"

    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id"), nullable=False)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_ahora_utc, nullable=False
    )
