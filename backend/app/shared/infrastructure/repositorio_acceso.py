"""Repositorio SQLAlchemy de acceso: usuarios + membresías (RF-1002).

Implementa el puerto `RepositorioAcceso` sobre los modelos de identidad
(`UsuarioModel`, `UsuarioNatilleraModel`) y `ParticipanteModel`. Es glue de
composición (cruza identidad y el tenant), por eso vive en `shared`, igual que
el resolver de principal y el asignador de membresías.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.modules.participantes.infrastructure.modelos import ParticipanteModel
from app.shared.application.gestion_acceso import (
    MembresiaRef,
    MiembroVista,
    UsuarioRef,
)
from app.shared.domain.acceso import ROL_ADMINISTRADOR
from app.shared.infrastructure.modelos_auth import UsuarioModel, UsuarioNatilleraModel


class RepositorioAccesoSQLAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _a_ref(self, usuario: UsuarioModel) -> UsuarioRef:
        return UsuarioRef(
            id=usuario.id,
            uuid=usuario.uuid,
            nombre=usuario.nombre,
            email=usuario.email,
            activo=usuario.activo,
        )

    def usuario_por_email(self, email: str) -> UsuarioRef | None:
        usuario = self._session.scalar(
            select(UsuarioModel).where(UsuarioModel.email == email)
        )
        return self._a_ref(usuario) if usuario is not None else None

    def usuario_por_uuid(self, uuid: str) -> UsuarioRef | None:
        usuario = self._session.scalar(
            select(UsuarioModel).where(UsuarioModel.uuid == uuid)
        )
        return self._a_ref(usuario) if usuario is not None else None

    def crear_usuario(self, nombre: str, email: str, hash_password: str) -> UsuarioRef:
        usuario = UsuarioModel(
            nombre=nombre, email=email, hash_password=hash_password, activo=True
        )
        self._session.add(usuario)
        self._session.flush()  # asigna id y uuid
        return self._a_ref(usuario)

    def actualizar_password(self, usuario_id: int, hash_password: str) -> None:
        self._session.execute(
            update(UsuarioModel)
            .where(UsuarioModel.id == usuario_id)
            .values(hash_password=hash_password)
        )

    def participante_id_por_uuid(
        self, natillera_id: int, participante_uuid: str
    ) -> int | None:
        return self._session.scalar(
            select(ParticipanteModel.id).where(
                ParticipanteModel.uuid == participante_uuid,
                ParticipanteModel.natillera_id == natillera_id,
            )
        )

    def membresia(self, usuario_id: int, natillera_id: int) -> MembresiaRef | None:
        fila = self._session.execute(
            select(
                UsuarioNatilleraModel.rol, UsuarioNatilleraModel.participante_id
            ).where(
                UsuarioNatilleraModel.usuario_id == usuario_id,
                UsuarioNatilleraModel.natillera_id == natillera_id,
            )
        ).first()
        if fila is None:
            return None
        return MembresiaRef(rol=fila[0], participante_id=fila[1])

    def crear_membresia(
        self, usuario_id: int, natillera_id: int, rol: str, participante_id: int | None
    ) -> None:
        self._session.add(
            UsuarioNatilleraModel(
                usuario_id=usuario_id,
                natillera_id=natillera_id,
                rol=rol,
                participante_id=participante_id,
            )
        )

    def actualizar_membresia(
        self, usuario_id: int, natillera_id: int, rol: str, participante_id: int | None
    ) -> None:
        self._session.execute(
            update(UsuarioNatilleraModel)
            .where(
                UsuarioNatilleraModel.usuario_id == usuario_id,
                UsuarioNatilleraModel.natillera_id == natillera_id,
            )
            .values(rol=rol, participante_id=participante_id)
        )

    def eliminar_membresia(self, usuario_id: int, natillera_id: int) -> None:
        self._session.execute(
            delete(UsuarioNatilleraModel).where(
                UsuarioNatilleraModel.usuario_id == usuario_id,
                UsuarioNatilleraModel.natillera_id == natillera_id,
            )
        )

    def contar_administradores(self, natillera_id: int) -> int:
        total = self._session.scalar(
            select(func.count())
            .select_from(UsuarioNatilleraModel)
            .where(
                UsuarioNatilleraModel.natillera_id == natillera_id,
                UsuarioNatilleraModel.rol == ROL_ADMINISTRADOR,
            )
        )
        return int(total or 0)

    def listar_miembros(self, natillera_id: int) -> list[MiembroVista]:
        filas = self._session.execute(
            select(
                UsuarioModel.uuid,
                UsuarioModel.nombre,
                UsuarioModel.email,
                UsuarioNatilleraModel.rol,
                UsuarioModel.activo,
                ParticipanteModel.uuid,
                ParticipanteModel.nombre,
            )
            .join(UsuarioModel, UsuarioNatilleraModel.usuario_id == UsuarioModel.id)
            .join(
                ParticipanteModel,
                UsuarioNatilleraModel.participante_id == ParticipanteModel.id,
                isouter=True,
            )
            .where(UsuarioNatilleraModel.natillera_id == natillera_id)
            .order_by(UsuarioModel.nombre)
        ).all()
        return [
            MiembroVista(
                usuario_uuid=f[0],
                nombre=f[1],
                email=f[2],
                rol=f[3],
                activo=f[4],
                participante_uuid=f[5],
                participante_nombre=f[6],
            )
            for f in filas
        ]
