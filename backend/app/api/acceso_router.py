"""Endpoints de gestión de usuarios y accesos (RF-1002, doc 07).

Todos operan dentro de una natillera (tenant) para que el RBAC resuelva el rol
del solicitante. Solo el ADMINISTRADOR gestiona accesos; ver la lista lo permite
también el SUPERVISOR. Routers finos: validan DTO → invocan el servicio → mapean.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.schemas_acceso import (
    AgregarMiembroRequest,
    AgregarMiembroResponse,
    CambiarRolRequest,
    MiembroResponse,
    ReiniciarClaveRequest,
)
from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_session
from app.core.errors import NoEncontrado
from app.core.security import hashear_password
from app.shared.application.gestion_acceso import ServicioAcceso
from app.shared.infrastructure.repositorio_acceso import RepositorioAccesoSQLAlchemy

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}/miembros", tags=["accesos"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


def obtener_servicio(session: Session = Depends(obtener_session)) -> ServicioAcceso:
    return ServicioAcceso(RepositorioAccesoSQLAlchemy(session), hashear_password)


def _tenant(principal: Principal) -> int:
    """El id del tenant resuelto por el RBAC. Si el rol está presente (lo exige
    require_rol) el id siempre lo está; este guard es defensa de tipos."""
    if principal.natillera_id is None:
        raise NoEncontrado("Natillera inexistente.")
    return principal.natillera_id


@router.get("", response_model=list[MiembroResponse])
def listar(
    principal: Principal = Depends(_ADMIN_SUP),
    servicio: ServicioAcceso = Depends(obtener_servicio),
) -> list[MiembroResponse]:
    miembros = servicio.listar(_tenant(principal))
    return [MiembroResponse(**vars(m)) for m in miembros]


@router.post("", response_model=AgregarMiembroResponse, status_code=201)
def agregar(
    datos: AgregarMiembroRequest,
    principal: Principal = Depends(_ADMIN),
    servicio: ServicioAcceso = Depends(obtener_servicio),
    session: Session = Depends(obtener_session),
) -> AgregarMiembroResponse:
    resultado = servicio.agregar(
        _tenant(principal),
        nombre=datos.nombre,
        email=datos.email,
        password=datos.password,
        rol=datos.rol,
        participante_uuid=datos.participante_uuid,
    )
    session.commit()
    return AgregarMiembroResponse(
        usuario_uuid=resultado.usuario_uuid, creado=resultado.creado
    )


@router.patch("/{usuario_uuid}", status_code=204, response_class=Response)
def cambiar_rol(
    usuario_uuid: str,
    datos: CambiarRolRequest,
    principal: Principal = Depends(_ADMIN),
    servicio: ServicioAcceso = Depends(obtener_servicio),
    session: Session = Depends(obtener_session),
) -> Response:
    servicio.cambiar_rol(
        _tenant(principal),
        usuario_uuid,
        rol=datos.rol,
        participante_uuid=datos.participante_uuid,
    )
    session.commit()
    return Response(status_code=204)


@router.delete("/{usuario_uuid}", status_code=204, response_class=Response)
def quitar(
    usuario_uuid: str,
    principal: Principal = Depends(_ADMIN),
    servicio: ServicioAcceso = Depends(obtener_servicio),
    session: Session = Depends(obtener_session),
) -> Response:
    servicio.quitar(_tenant(principal), usuario_uuid)
    session.commit()
    return Response(status_code=204)


@router.post("/{usuario_uuid}/clave", status_code=204, response_class=Response)
def reiniciar_clave(
    usuario_uuid: str,
    datos: ReiniciarClaveRequest,
    principal: Principal = Depends(_ADMIN),
    servicio: ServicioAcceso = Depends(obtener_servicio),
    session: Session = Depends(obtener_session),
) -> Response:
    servicio.reiniciar_clave(_tenant(principal), usuario_uuid, datos.password)
    session.commit()
    return Response(status_code=204)
