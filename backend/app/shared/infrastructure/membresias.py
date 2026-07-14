"""Implementación de asignación de membresías (RF-1002)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.shared.infrastructure.modelos_auth import UsuarioNatilleraModel


class AsignadorMembresiaSQLAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def asignar(self, usuario_id: int, natillera_id: int, rol: str) -> None:
        existe = self._session.scalar(
            select(UsuarioNatilleraModel).where(
                UsuarioNatilleraModel.usuario_id == usuario_id,
                UsuarioNatilleraModel.natillera_id == natillera_id,
            )
        )
        if existe is None:
            self._session.add(
                UsuarioNatilleraModel(
                    usuario_id=usuario_id, natillera_id=natillera_id, rol=rol
                )
            )
