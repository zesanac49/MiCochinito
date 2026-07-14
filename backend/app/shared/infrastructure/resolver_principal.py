"""Resolver de principal contra la BD (RBAC por tenant, RF-1002, RNF-02).

Composición de identidad: dado el usuario del token y la natillera de la ruta,
resuelve la membresía (rol y participante vinculado). Vive en shared porque es
glue de composición que cruza usuarios (identidad) y natilleras/participantes.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol
from app.modules.natilleras.infrastructure.modelos import NatilleraModel
from app.modules.participantes.infrastructure.modelos import ParticipanteModel
from app.shared.infrastructure.modelos_auth import UsuarioModel, UsuarioNatilleraModel


class ResolverPrincipalSQLAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def resolver(self, usuario_uuid: str, natillera_uuid: str | None) -> Principal:
        usuario = self._session.scalar(
            select(UsuarioModel).where(UsuarioModel.uuid == usuario_uuid)
        )
        if usuario is None:
            return Principal(usuario_uuid=usuario_uuid, natillera_uuid=natillera_uuid)

        base = Principal(
            usuario_uuid=usuario_uuid,
            usuario_id=usuario.id,
            natillera_uuid=natillera_uuid,
        )
        if natillera_uuid is None:
            return base

        natillera = self._session.scalar(
            select(NatilleraModel).where(NatilleraModel.uuid == natillera_uuid)
        )
        if natillera is None:
            return base

        membresia = self._session.scalar(
            select(UsuarioNatilleraModel).where(
                UsuarioNatilleraModel.usuario_id == usuario.id,
                UsuarioNatilleraModel.natillera_id == natillera.id,
            )
        )
        if membresia is None:
            # Autenticado pero sin membresía en este tenant: sin rol => 403.
            return Principal(
                usuario_uuid=usuario_uuid,
                usuario_id=usuario.id,
                natillera_uuid=natillera_uuid,
                natillera_id=natillera.id,
            )

        participante_uuid: str | None = None
        if membresia.participante_id is not None:
            part = self._session.get(ParticipanteModel, membresia.participante_id)
            participante_uuid = part.uuid if part is not None else None

        return Principal(
            usuario_uuid=usuario_uuid,
            usuario_id=usuario.id,
            natillera_uuid=natillera_uuid,
            natillera_id=natillera.id,
            rol=Rol(membresia.rol),
            participante_uuid=participante_uuid,
        )
