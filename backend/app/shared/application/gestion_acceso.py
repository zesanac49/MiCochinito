"""Gestión de usuarios y accesos por natillera (RF-1002, doc 07).

Capa de aplicación: orquesta identidad (usuarios) y membresías (rol por tenant)
sobre un puerto de persistencia, aplicando las reglas del dominio. No conoce
SQLAlchemy: recibe un `RepositorioAcceso` (Protocol) y un `hasher` inyectados.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.shared.domain.acceso import (
    MiembroNoEncontrado,
    MiembroYaExiste,
    ParticipanteNoEncontrado,
    normalizar_participante,
    validar_rol,
    verificar_no_ultimo_admin,
)


@dataclass(frozen=True)
class UsuarioRef:
    """Vista mínima de un usuario para la capa de aplicación (sin ORM)."""

    id: int
    uuid: str
    nombre: str
    email: str
    activo: bool


@dataclass(frozen=True)
class MembresiaRef:
    rol: str
    participante_id: int | None


@dataclass(frozen=True)
class MiembroVista:
    """Fila de la lista de miembros de una natillera."""

    usuario_uuid: str
    nombre: str
    email: str
    rol: str
    activo: bool
    participante_uuid: str | None
    participante_nombre: str | None


@dataclass(frozen=True)
class ResultadoAgregar:
    usuario_uuid: str
    creado: bool  # True si se creó un usuario nuevo; False si se vinculó uno existente


class RepositorioAcceso(Protocol):
    """Puerto de persistencia de identidad + membresías (impl. en infrastructure)."""

    def usuario_por_email(self, email: str) -> UsuarioRef | None: ...

    def usuario_por_uuid(self, uuid: str) -> UsuarioRef | None: ...

    def crear_usuario(self, nombre: str, email: str, hash_password: str) -> UsuarioRef: ...

    def actualizar_password(self, usuario_id: int, hash_password: str) -> None: ...

    def participante_id_por_uuid(
        self, natillera_id: int, participante_uuid: str
    ) -> int | None: ...

    def membresia(self, usuario_id: int, natillera_id: int) -> MembresiaRef | None: ...

    def crear_membresia(
        self, usuario_id: int, natillera_id: int, rol: str, participante_id: int | None
    ) -> None: ...

    def actualizar_membresia(
        self, usuario_id: int, natillera_id: int, rol: str, participante_id: int | None
    ) -> None: ...

    def eliminar_membresia(self, usuario_id: int, natillera_id: int) -> None: ...

    def contar_administradores(self, natillera_id: int) -> int: ...

    def listar_miembros(self, natillera_id: int) -> list[MiembroVista]: ...


class ServicioAcceso:
    """Casos de uso de gestión de accesos (RF-1002). Todos operan en el contexto
    de una natillera (tenant); el `natillera_id` lo aporta el principal ya
    resuelto por el RBAC."""

    def __init__(
        self, repo: RepositorioAcceso, hasher: Callable[[str], str]
    ) -> None:
        self._repo = repo
        self._hasher = hasher

    def listar(self, natillera_id: int) -> list[MiembroVista]:
        return self._repo.listar_miembros(natillera_id)

    def agregar(
        self,
        natillera_id: int,
        *,
        nombre: str,
        email: str,
        password: str,
        rol: str,
        participante_uuid: str | None,
    ) -> ResultadoAgregar:
        validar_rol(rol)
        participante_id = self._resolver_participante(natillera_id, rol, participante_uuid)

        usuario = self._repo.usuario_por_email(email)
        creado = False
        if usuario is None:
            usuario = self._repo.crear_usuario(nombre, email, self._hasher(password))
            creado = True
        elif self._repo.membresia(usuario.id, natillera_id) is not None:
            raise MiembroYaExiste("El usuario ya es miembro de esta natillera.")

        self._repo.crear_membresia(usuario.id, natillera_id, rol, participante_id)
        return ResultadoAgregar(usuario_uuid=usuario.uuid, creado=creado)

    def cambiar_rol(
        self,
        natillera_id: int,
        usuario_uuid: str,
        *,
        rol: str,
        participante_uuid: str | None,
    ) -> None:
        validar_rol(rol)
        usuario, membresia = self._miembro(natillera_id, usuario_uuid)
        participante_id = self._resolver_participante(natillera_id, rol, participante_uuid)
        verificar_no_ultimo_admin(
            membresia.rol, rol, self._repo.contar_administradores(natillera_id)
        )
        self._repo.actualizar_membresia(usuario.id, natillera_id, rol, participante_id)

    def quitar(self, natillera_id: int, usuario_uuid: str) -> None:
        usuario, membresia = self._miembro(natillera_id, usuario_uuid)
        verificar_no_ultimo_admin(
            membresia.rol, None, self._repo.contar_administradores(natillera_id)
        )
        self._repo.eliminar_membresia(usuario.id, natillera_id)

    def reiniciar_clave(
        self, natillera_id: int, usuario_uuid: str, nueva_password: str
    ) -> None:
        usuario, _ = self._miembro(natillera_id, usuario_uuid)
        self._repo.actualizar_password(usuario.id, self._hasher(nueva_password))

    # --- Auxiliares --------------------------------------------------------

    def _miembro(
        self, natillera_id: int, usuario_uuid: str
    ) -> tuple[UsuarioRef, MembresiaRef]:
        """Resuelve un usuario y su membresía en esta natillera; si no es miembro
        (o no existe), es indistinguible de 'no encontrado' para el admin."""
        usuario = self._repo.usuario_por_uuid(usuario_uuid)
        if usuario is None:
            raise MiembroNoEncontrado("Miembro no encontrado en esta natillera.")
        membresia = self._repo.membresia(usuario.id, natillera_id)
        if membresia is None:
            raise MiembroNoEncontrado("Miembro no encontrado en esta natillera.")
        return usuario, membresia

    def _resolver_participante(
        self, natillera_id: int, rol: str, participante_uuid: str | None
    ) -> int | None:
        participante_id: int | None = None
        if participante_uuid is not None:
            participante_id = self._repo.participante_id_por_uuid(
                natillera_id, participante_uuid
            )
            if participante_id is None:
                raise ParticipanteNoEncontrado(
                    "El participante indicado no existe en esta natillera."
                )
        # Aplica la regla CLIENTE↔participante y descarta el vínculo en otros roles.
        return normalizar_participante(rol, participante_id)
