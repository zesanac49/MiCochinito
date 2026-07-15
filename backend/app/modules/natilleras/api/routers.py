"""Endpoints de natilleras (RF-101/102/103/104, doc 07).

Routers finos: validan DTO → invocan caso de uso → mapean respuesta.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import Principal, Rol, obtener_principal_actual, require_rol
from app.core.errors import NoEncontrado
from app.modules.natilleras.api.deps import (
    obtener_repo,
    uc_configurar,
    uc_crear,
    uc_regenerar_periodos,
    uc_transicionar,
)
from app.modules.natilleras.api.schemas import (
    ConfiguracionRequest,
    CrearNatilleraRequest,
    NatilleraResponse,
    TransicionRequest,
)
from app.modules.natilleras.application.casos_uso import (
    ConfigurarNatillera,
    CrearNatillera,
    RegenerarPeriodos,
    TransicionarEstado,
)
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)

router = APIRouter(prefix="/api/v1/natilleras", tags=["natilleras"])

_MIEMBRO = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.CLIENTE)
_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


@router.post("", response_model=NatilleraResponse, status_code=201)
def crear(
    datos: CrearNatilleraRequest,
    uc: CrearNatillera = Depends(uc_crear),
    principal: Principal = Depends(obtener_principal_actual),
) -> NatilleraResponse:
    cfg = datos.configuracion.a_dominio() if datos.configuracion else None
    natillera = uc.ejecutar(
        datos.nombre, datos.ciclo_inicio, datos.ciclo_fin, principal.usuario_id or 0, cfg
    )
    return NatilleraResponse.de_dominio(natillera)


@router.get("", response_model=list[NatilleraResponse])
def listar(
    principal: Principal = Depends(obtener_principal_actual),
    repo: RepositorioNatillerasSQLAlchemy = Depends(obtener_repo),
) -> list[NatilleraResponse]:
    usuario_id = principal.usuario_id or 0
    return [NatilleraResponse.de_dominio(n) for n in repo.listar_de_usuario(usuario_id)]


@router.get("/{natillera_uuid}", response_model=NatilleraResponse)
def obtener(
    natillera_uuid: str,
    principal: Principal = Depends(_MIEMBRO),
    repo: RepositorioNatillerasSQLAlchemy = Depends(obtener_repo),
) -> NatilleraResponse:
    natillera = repo.obtener_por_uuid(natillera_uuid)
    if natillera is None:
        raise NoEncontrado("Natillera inexistente.")
    return NatilleraResponse.de_dominio(natillera)


@router.post("/{natillera_uuid}/transiciones", response_model=NatilleraResponse)
def transicionar(
    natillera_uuid: str,
    datos: TransicionRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    uc: TransicionarEstado = Depends(uc_transicionar),
) -> NatilleraResponse:
    autor_id = principal.usuario_id or 0
    natillera = uc.ejecutar(natillera_uuid, datos.a, autor_id)
    return NatilleraResponse.de_dominio(natillera)


@router.put("/{natillera_uuid}/configuracion", response_model=NatilleraResponse)
def configurar(
    natillera_uuid: str,
    datos: ConfiguracionRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    uc: ConfigurarNatillera = Depends(uc_configurar),
) -> NatilleraResponse:
    autor_id = principal.usuario_id or 0
    natillera = uc.ejecutar(natillera_uuid, datos.a_dominio(), autor_id)
    return NatilleraResponse.de_dominio(natillera)


@router.post("/{natillera_uuid}/periodos/regenerar", response_model=dict[str, int])
def regenerar_periodos(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    uc: RegenerarPeriodos = Depends(uc_regenerar_periodos),
) -> dict[str, int]:
    """Sincroniza los períodos con la periodicidad configurada (aditivo)."""
    creados = uc.ejecutar(natillera_uuid)
    return {"periodos_creados": creados}
