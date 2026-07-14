"""Almacén de refresh tokens en BD (rotación/revocación, RF-1001, doc 04 §3.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.shared.infrastructure.modelos_auth import RefreshTokenModel, UsuarioModel


class AlmacenRefreshTokensSQLAlchemy:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def registrar(self, jti: str, usuario_uuid: str) -> None:
        usuario_id = self._session.scalar(
            select(UsuarioModel.id).where(UsuarioModel.uuid == usuario_uuid)
        )
        if usuario_id is None:
            return
        expira = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_dias)
        self._session.add(
            RefreshTokenModel(
                usuario_id=usuario_id, jti=jti, expira_en=expira, revocado=False
            )
        )

    def esta_activo(self, jti: str) -> bool:
        fila = self._session.scalar(
            select(RefreshTokenModel).where(
                RefreshTokenModel.jti == jti, RefreshTokenModel.revocado.is_(False)
            )
        )
        return fila is not None

    def revocar(self, jti: str) -> None:
        fila = self._session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.jti == jti)
        )
        if fila is not None:
            fila.revocado = True
