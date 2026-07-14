"""Endpoints de multas y catálogo (RF-601/602/603, doc 07)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.errors import NoEncontrado
from app.core.eventbus import BusDeEventos
from app.modules.multas.api.deps import repo_catalogo, repo_multas, servicio_multas
from app.modules.multas.api.schemas import (
    AnularMultaRequest,
    CatalogoResponse,
    CrearCatalogoRequest,
    ImponerMultaRequest,
    MultaResponse,
)
from app.modules.participantes.api.deps import natillera_id_de

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}", tags=["multas"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


@router.get("/catalogo-multas", response_model=list[CatalogoResponse])
def listar_catalogo(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[CatalogoResponse]:
    entradas = repo_catalogo(session, natillera_id_de(principal)).listar()
    return [CatalogoResponse.de_entrada(e) for e in entradas]


@router.post("/catalogo-multas", response_model=CatalogoResponse, status_code=201)
def crear_catalogo(
    natillera_uuid: str,
    datos: CrearCatalogoRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> CatalogoResponse:
    svc = servicio_multas(session, bus, natillera_id_de(principal))
    entrada = svc.crear_catalogo(natillera_uuid, datos.nombre, datos.tipo, Decimal(datos.valor))
    return CatalogoResponse.de_entrada(entrada)


@router.post("/multas", response_model=MultaResponse, status_code=201)
def imponer(
    natillera_uuid: str,
    datos: ImponerMultaRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> MultaResponse:
    nid = natillera_id_de(principal)
    catalogo_id: int | None = None
    if datos.catalogo_uuid:
        entrada = repo_catalogo(session, nid).obtener_por_uuid(datos.catalogo_uuid)
        if entrada is None:
            raise NoEncontrado("Entrada de catálogo inexistente.")
        catalogo_id = entrada.id
    valor = Decimal(datos.valor) if datos.valor else None
    svc = servicio_multas(session, bus, nid)
    m = svc.imponer(natillera_uuid, datos.participante_uuid, datos.motivo, catalogo_id, valor)
    return MultaResponse.de_dominio(m)


@router.get("/multas", response_model=list[MultaResponse])
def listar(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[MultaResponse]:
    multas = repo_multas(session, natillera_id_de(principal)).listar()
    return [MultaResponse.de_dominio(m) for m in multas]


@router.post("/multas/{multa_uuid}/pago", response_model=MultaResponse)
def pagar(
    natillera_uuid: str,
    multa_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> MultaResponse:
    svc = servicio_multas(session, bus, natillera_id_de(principal))
    resultado = svc.pagar(natillera_uuid, multa_uuid, principal.usuario_id or 0)
    return MultaResponse.de_dominio(resultado.multa)


@router.post("/multas/{multa_uuid}/anulacion", response_model=MultaResponse)
def anular(
    natillera_uuid: str,
    multa_uuid: str,
    datos: AnularMultaRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> MultaResponse:
    svc = servicio_multas(session, bus, natillera_id_de(principal))
    m = svc.anular(natillera_uuid, multa_uuid, datos.justificacion, principal.usuario_id or 0)
    return MultaResponse.de_dominio(m)
