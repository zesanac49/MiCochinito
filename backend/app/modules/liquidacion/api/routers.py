"""Endpoints de liquidación (RF-701..706, doc 07)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.eventbus import BusDeEventos
from app.modules.liquidacion.api.deps import repo_participantes, servicio_liquidacion
from app.modules.liquidacion.api.schemas import (
    ConfirmacionRequest,
    DecisionRequest,
    EntregaRequest,
    LiquidacionResponse,
)
from app.modules.liquidacion.domain.liquidacion import Bloqueo, Liquidacion
from app.modules.participantes.api.deps import natillera_id_de

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}/liquidacion", tags=["liquidacion"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


def _respuesta(
    session: Session, nid: int, liq: Liquidacion | None, bloqueos: list[Bloqueo]
) -> LiquidacionResponse:
    ids = [d.participante_id for d in liq.detalles] if liq else []
    nombres = repo_participantes(session, nid).nombres_por_id(ids)
    return LiquidacionResponse.de_dominio(liq, bloqueos, nombres)


@router.post("", response_model=LiquidacionResponse, status_code=201)
def iniciar(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    nid = natillera_id_de(principal)
    liq, bloqueos = servicio_liquidacion(session, bus, nid).iniciar(natillera_uuid)
    return _respuesta(session, nid, liq, bloqueos)


@router.get("", response_model=LiquidacionResponse)
def obtener(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    nid = natillera_id_de(principal)
    liq, bloqueos = servicio_liquidacion(session, bus, nid).obtener(natillera_uuid)
    return _respuesta(session, nid, liq, bloqueos)


@router.post("/decisiones", response_model=LiquidacionResponse)
def decidir(
    natillera_uuid: str,
    datos: DecisionRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    nid = natillera_id_de(principal)
    svc = servicio_liquidacion(session, bus, nid)
    svc.resolver_bloqueo(
        natillera_uuid, datos.tipo_bloqueo, datos.origen_tipo, datos.origen_id,
        datos.decision, principal.usuario_id or 0,
    )
    liq, bloqueos = svc.obtener(natillera_uuid)
    return _respuesta(session, nid, liq, bloqueos)


@router.post("/calculo", response_model=LiquidacionResponse)
def calcular(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    nid = natillera_id_de(principal)
    liq = servicio_liquidacion(session, bus, nid).calcular(natillera_uuid, date.today())
    return _respuesta(session, nid, liq, [])


@router.post("/confirmacion", response_model=LiquidacionResponse)
def confirmar(
    natillera_uuid: str,
    datos: ConfirmacionRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    nid = natillera_id_de(principal)
    liq = servicio_liquidacion(session, bus, nid).confirmar(
        natillera_uuid, datos.nombre_natillera, principal.usuario_id or 0
    )
    return _respuesta(session, nid, liq, [])


@router.get("/acta", response_model=LiquidacionResponse)
def acta(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> LiquidacionResponse:
    # El acta son los datos de la liquidación confirmada; el PDF lo genera el cliente.
    nid = natillera_id_de(principal)
    liq, _ = servicio_liquidacion(session, bus, nid).obtener(natillera_uuid)
    return _respuesta(session, nid, liq, [])


@router.post("/entregas", status_code=204, response_class=Response)
def registrar_entrega(
    natillera_uuid: str,
    datos: EntregaRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> Response:
    nid = natillera_id_de(principal)
    servicio_liquidacion(session, bus, nid).registrar_entrega(
        natillera_uuid, datos.participante_uuid, principal.usuario_id or 0
    )
    return Response(status_code=204)
