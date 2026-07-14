"""Endpoints de cuotas, lote y aportes (RF-301/302/303, doc 07).

Los POST de pago individual y aporte aceptan `Idempotency-Key` (doc 07 §1):
misma clave+payload replica el resultado; payload distinto → 409.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.api.schemas import AsientoResponse
from app.modules.contabilidad.infrastructure.repositorios import (
    RepositorioLedgerSQLAlchemy,
)
from app.modules.cuotas.api.deps import servicio_cuotas
from app.modules.cuotas.api.schemas import (
    AporteRequest,
    PagoCuotaRequest,
    PagoLoteRequest,
    ResumenLoteResponse,
)
from app.modules.participantes.api.deps import natillera_id_de
from app.shared.domain.dinero import Dinero
from app.shared.infrastructure.idempotencia import ServicioIdempotencia

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}", tags=["cuotas"])

_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


def _replay(
    session: Session, natillera_id: int, clave: str | None, payload: dict[str, object]
) -> AsientoResponse | None:
    """Devuelve la respuesta original si la clave ya se procesó (idempotencia)."""
    if not clave:
        return None
    ref = ServicioIdempotencia(session, natillera_id).buscar_replay(clave, payload)
    if ref is None:
        return None
    asiento = RepositorioLedgerSQLAlchemy(session, natillera_id).obtener_por_uuid(ref)
    return AsientoResponse.de_leido(asiento) if asiento is not None else None


def _guardar_clave(
    session: Session,
    natillera_id: int,
    clave: str | None,
    payload: dict[str, object],
    referencia_uuid: str,
) -> None:
    if clave:
        ServicioIdempotencia(session, natillera_id).registrar(clave, payload, referencia_uuid)
        session.commit()


@router.post("/cuotas/pagos", response_model=AsientoResponse, status_code=201)
def pagar_cuota(
    natillera_uuid: str,
    datos: PagoCuotaRequest,
    request: Request,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> AsientoResponse:
    nid = natillera_id_de(principal)
    clave = request.headers.get("Idempotency-Key")
    payload = datos.model_dump()
    replay = _replay(session, nid, clave, payload)
    if replay is not None:
        return replay
    svc = servicio_cuotas(session, bus, nid)
    leido = svc.pagar_cuota(
        natillera_uuid, datos.participante_uuid, datos.periodo_uuid, principal.usuario_id or 0
    )
    _guardar_clave(session, nid, clave, payload, leido.uuid)
    return AsientoResponse.de_leido(leido)


@router.post("/aportes-extraordinarios", response_model=AsientoResponse, status_code=201)
def registrar_aporte(
    natillera_uuid: str,
    datos: AporteRequest,
    request: Request,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> AsientoResponse:
    nid = natillera_id_de(principal)
    clave = request.headers.get("Idempotency-Key")
    payload = datos.model_dump()
    replay = _replay(session, nid, clave, payload)
    if replay is not None:
        return replay
    svc = servicio_cuotas(session, bus, nid)
    leido = svc.registrar_aporte(
        natillera_uuid, datos.participante_uuid, Dinero(datos.monto), principal.usuario_id or 0
    )
    _guardar_clave(session, nid, clave, payload, leido.uuid)
    return AsientoResponse.de_leido(leido)


@router.post("/cuotas/pagos-lote", response_model=ResumenLoteResponse)
def pagar_lote(
    natillera_uuid: str,
    datos: PagoLoteRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ResumenLoteResponse:
    nid = natillera_id_de(principal)
    svc = servicio_cuotas(session, bus, nid)
    items = [(i.participante_uuid, i.periodo_uuid) for i in datos.items]
    resumen = svc.pagar_lote(natillera_uuid, items, principal.usuario_id or 0)
    return ResumenLoteResponse.de_dto(resumen)
