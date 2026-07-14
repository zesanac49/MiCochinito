"""Endpoints de préstamos (RF-401..406, doc 07)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.errors import NoEncontrado
from app.core.eventbus import BusDeEventos
from app.modules.participantes.api.deps import natillera_id_de
from app.modules.prestamos.api.deps import repo_prestamos, servicio_prestamos
from app.modules.prestamos.api.schemas import (
    AprobacionRequest,
    DescomposicionResponse,
    PagoPrestamoRequest,
    PagoPrestamoResponse,
    PrestamoResponse,
    SolicitarPrestamoRequest,
)
from app.shared.domain.dinero import Dinero
from app.shared.infrastructure.idempotencia import ServicioIdempotencia

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}/prestamos", tags=["prestamos"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


@router.post("", response_model=PrestamoResponse, status_code=201)
def solicitar(
    natillera_uuid: str,
    datos: SolicitarPrestamoRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> PrestamoResponse:
    svc = servicio_prestamos(session, bus, natillera_id_de(principal))
    p = svc.solicitar(
        natillera_uuid,
        datos.participante_uuid,
        Dinero(datos.capital),
        Decimal(datos.tasa),
        datos.plazo_meses,
    )
    return PrestamoResponse.de_dominio(p)


@router.get("", response_model=list[PrestamoResponse])
def listar(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[PrestamoResponse]:
    repo = repo_prestamos(session, natillera_id_de(principal))
    return [PrestamoResponse.de_dominio(p) for p in repo.listar()]


@router.get("/{prestamo_uuid}", response_model=PrestamoResponse)
def obtener(
    natillera_uuid: str,
    prestamo_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> PrestamoResponse:
    p = repo_prestamos(session, natillera_id_de(principal)).obtener_por_uuid(prestamo_uuid)
    if p is None:
        raise NoEncontrado("Préstamo inexistente.")
    return PrestamoResponse.de_dominio(p)


@router.post("/{prestamo_uuid}/aprobacion", response_model=PrestamoResponse)
def aprobacion(
    natillera_uuid: str,
    prestamo_uuid: str,
    datos: AprobacionRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> PrestamoResponse:
    svc = servicio_prestamos(session, bus, natillera_id_de(principal))
    p = svc.decidir(natillera_uuid, prestamo_uuid, datos.aprobar, datos.motivo)
    return PrestamoResponse.de_dominio(p)


@router.post("/{prestamo_uuid}/desembolso", response_model=PrestamoResponse)
def desembolso(
    natillera_uuid: str,
    prestamo_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> PrestamoResponse:
    svc = servicio_prestamos(session, bus, natillera_id_de(principal))
    p = svc.desembolsar(natillera_uuid, prestamo_uuid, date.today(), principal.usuario_id or 0)
    return PrestamoResponse.de_dominio(p)


@router.post("/{prestamo_uuid}/pagos", response_model=PagoPrestamoResponse, status_code=201)
def pagar(
    natillera_uuid: str,
    prestamo_uuid: str,
    datos: PagoPrestamoRequest,
    request: Request,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> PagoPrestamoResponse:
    nid = natillera_id_de(principal)
    clave = request.headers.get("Idempotency-Key")
    payload = datos.model_dump()
    idem = ServicioIdempotencia(session, nid)
    if clave and idem.buscar_replay(clave, payload) is not None:
        # Ya procesado: devuelve el estado actual sin registrar un segundo pago.
        p = repo_prestamos(session, nid).obtener_por_uuid(prestamo_uuid)
        if p is None:
            raise NoEncontrado("Préstamo inexistente.")
        return PagoPrestamoResponse(
            descomposicion=DescomposicionResponse(capital="0.00", interes="0.00", total="0.00"),
            prestamo=PrestamoResponse.de_dominio(p),
            asientos=[],
        )
    svc = servicio_prestamos(session, bus, nid)
    resultado = svc.pagar(
        natillera_uuid, prestamo_uuid, Dinero(datos.monto), date.today(), principal.usuario_id or 0
    )
    if clave:
        assert resultado.prestamo.uuid is not None
        idem.registrar(clave, payload, resultado.prestamo.uuid)
        session.commit()
    return PagoPrestamoResponse.de_resultado(resultado)


@router.post("/mora", response_model=dict)
def detectar_mora(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> dict[str, int]:
    svc = servicio_prestamos(session, bus, natillera_id_de(principal))
    marcados = svc.detectar_mora(natillera_uuid, date.today())
    return {"marcados_en_mora": marcados}
