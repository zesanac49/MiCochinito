"""Repositorio de usuarios (identidad transversal, RF-1001/1002)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.infrastructure.modelos_auth import UsuarioModel


class RepositorioUsuarios:
    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener_por_email(self, email: str) -> UsuarioModel | None:
        return self._session.scalar(select(UsuarioModel).where(UsuarioModel.email == email))

    def obtener_por_uuid(self, uuid: str) -> UsuarioModel | None:
        return self._session.scalar(select(UsuarioModel).where(UsuarioModel.uuid == uuid))
