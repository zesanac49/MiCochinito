"""Endpoints de actividades y polla (RF-501..508, doc 07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.errors import NoEncontrado
from app.core.eventbus import BusDeEventos
from app.modules.actividades.api.deps import repo_actividades, servicio_actividades
from app.modules.actividades.api.schemas import (
    ActividadResponse,
    AsignarNumerosRequest,
    ClonacionRequest,
    CrearActividadRequest,
    MovimientoRequest,
    PagoNumerosRequest,
    SorteoRequest,
)
from app.modules.participantes.api.deps import natillera_id_de
from app.shared.domain.dinero import Dinero

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}/actividades", tags=["actividades"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)
_MIEMBRO = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.CLIENTE)


def _dinero(v: str | None) -> Dinero | None:
    return Dinero(v) if v else None


@router.post("", response_model=ActividadResponse, status_code=201)
def crear(
    natillera_uuid: str,
    datos: CrearActividadRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    a = svc.crear(
        natillera_uuid,
        datos.tipo,
        datos.nombre,
        datos.periodo_uuid,
        _dinero(datos.valor_numero),
        datos.cantidad_numeros,
        _dinero(datos.premio),
        datos.fecha_sorteo,
    )
    return ActividadResponse.de_dominio(a)


@router.get("", response_model=list[ActividadResponse])
def listar(
    natillera_uuid: str,
    principal: Principal = Depends(_MIEMBRO),
    session: Session = Depends(obtener_session),
) -> list[ActividadResponse]:
    acts = repo_actividades(session, natillera_id_de(principal)).listar()
    return [ActividadResponse.de_dominio(a) for a in acts]


@router.get("/{actividad_uuid}", response_model=ActividadResponse)
def obtener(
    natillera_uuid: str,
    actividad_uuid: str,
    principal: Principal = Depends(_MIEMBRO),
    session: Session = Depends(obtener_session),
) -> ActividadResponse:
    a = repo_actividades(session, natillera_id_de(principal)).obtener_por_uuid(actividad_uuid)
    if a is None:
        raise NoEncontrado("Actividad inexistente.")
    return ActividadResponse.de_dominio(a)


@router.post("/{actividad_uuid}/apertura", response_model=ActividadResponse)
def abrir(
    natillera_uuid: str,
    actividad_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(svc.abrir(natillera_uuid, actividad_uuid))


@router.put("/{actividad_uuid}/numeros", response_model=ActividadResponse)
def asignar_numeros(
    natillera_uuid: str,
    actividad_uuid: str,
    datos: AsignarNumerosRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    asignaciones = [(a.numero, a.participante_uuid) for a in datos.asignaciones]
    return ActividadResponse.de_dominio(
        svc.asignar_numeros(natillera_uuid, actividad_uuid, asignaciones)
    )


@router.post("/{actividad_uuid}/numeros/pagos", response_model=ActividadResponse)
def pagar_numeros(
    natillera_uuid: str,
    actividad_uuid: str,
    datos: PagoNumerosRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(
        svc.registrar_pago_numeros(natillera_uuid, actividad_uuid, datos.numeros)
    )


@router.post("/{actividad_uuid}/movimientos", response_model=ActividadResponse)
def registrar_movimiento(
    natillera_uuid: str,
    actividad_uuid: str,
    datos: MovimientoRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(
        svc.registrar_movimiento(
            natillera_uuid, actividad_uuid, datos.tipo, datos.concepto, Dinero(datos.valor)
        )
    )


@router.post("/{actividad_uuid}/sorteo", response_model=ActividadResponse)
def sortear(
    natillera_uuid: str,
    actividad_uuid: str,
    datos: SorteoRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(
        svc.sortear(natillera_uuid, actividad_uuid, datos.numero_ganador, datos.fuente)
    )


@router.post("/{actividad_uuid}/cierre", response_model=ActividadResponse)
def cerrar(
    natillera_uuid: str,
    actividad_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(
        svc.cerrar(natillera_uuid, actividad_uuid, principal.usuario_id or 0)
    )


@router.post("/{actividad_uuid}/clonacion", response_model=ActividadResponse, status_code=201)
def clonar(
    natillera_uuid: str,
    actividad_uuid: str,
    datos: ClonacionRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ActividadResponse:
    svc = servicio_actividades(session, bus, natillera_id_de(principal))
    return ActividadResponse.de_dominio(
        svc.clonar(natillera_uuid, actividad_uuid, datos.periodo_destino_uuid)
    )
