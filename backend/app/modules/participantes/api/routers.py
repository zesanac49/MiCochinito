"""Endpoints de participantes (RF-201/202, doc 07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_bus, obtener_session
from app.core.errors import NoEncontrado, Prohibido
from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.api.schemas import AsientoResponse
from app.modules.contabilidad.domain.conceptos import Naturaleza, TipoFondo
from app.modules.contabilidad.infrastructure.repositorios import (
    RepositorioLedgerSQLAlchemy,
)
from app.modules.participantes.api.deps import (
    cambiar_estado_uc,
    editar_contacto_uc,
    fijar_cuota_uc,
    inscribir_uc,
    natillera_id_de,
    repo_de,
)
from app.modules.participantes.api.schemas import (
    CambiarEstadoRequest,
    CuentaResponse,
    EditarContactoRequest,
    FijarCuotaRequest,
    InscribirParticipanteRequest,
    ParticipanteResponse,
    SaldosResponse,
)
from app.modules.participantes.domain.participante import EstadoParticipante
from app.shared.domain.dinero import Dinero

router = APIRouter(
    prefix="/api/v1/natilleras/{natillera_uuid}/participantes", tags=["participantes"]
)

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)
_MIEMBRO = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR, Rol.CLIENTE)


@router.post("", response_model=ParticipanteResponse, status_code=201)
def inscribir(
    natillera_uuid: str,
    datos: InscribirParticipanteRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ParticipanteResponse:
    uc = inscribir_uc(session, bus, natillera_id_de(principal))
    p = uc.ejecutar(
        natillera_uuid,
        datos.nombre,
        datos.documento(),
        datos.fecha_ingreso,
        datos.telefono,
        datos.direccion,
        Dinero(datos.valor_cuota) if datos.valor_cuota else None,
    )
    return ParticipanteResponse.de_dominio(p)


@router.get("", response_model=list[ParticipanteResponse])
def listar(
    natillera_uuid: str,
    estado: EstadoParticipante | None = None,
    q: str | None = None,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[ParticipanteResponse]:
    repo = repo_de(session, natillera_id_de(principal))
    return [ParticipanteResponse.de_dominio(p) for p in repo.listar(estado=estado, q=q)]


@router.get("/{participante_uuid}", response_model=ParticipanteResponse)
def obtener(
    natillera_uuid: str,
    participante_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> ParticipanteResponse:
    repo = repo_de(session, natillera_id_de(principal))
    p = repo.obtener_por_uuid(participante_uuid)
    if p is None:
        raise NoEncontrado("Participante inexistente.")
    return ParticipanteResponse.de_dominio(p)


@router.put("/{participante_uuid}", response_model=ParticipanteResponse)
def editar(
    natillera_uuid: str,
    participante_uuid: str,
    datos: EditarContactoRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ParticipanteResponse:
    uc = editar_contacto_uc(session, bus, natillera_id_de(principal))
    p = uc.ejecutar(participante_uuid, datos.telefono, datos.direccion)
    return ParticipanteResponse.de_dominio(p)


@router.put("/{participante_uuid}/cuota", response_model=ParticipanteResponse)
def fijar_cuota(
    natillera_uuid: str,
    participante_uuid: str,
    datos: FijarCuotaRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ParticipanteResponse:
    uc = fijar_cuota_uc(session, bus, natillera_id_de(principal))
    p = uc.ejecutar(participante_uuid, Dinero(datos.valor_cuota))
    return ParticipanteResponse.de_dominio(p)


@router.get("/{participante_uuid}/cuenta", response_model=CuentaResponse)
def cuenta(
    natillera_uuid: str,
    participante_uuid: str,
    principal: Principal = Depends(_MIEMBRO),
    session: Session = Depends(obtener_session),
) -> CuentaResponse:
    nid = natillera_id_de(principal)
    # CLI solo puede ver su propia cuenta (RF-203).
    if principal.rol is Rol.CLIENTE and principal.participante_uuid != participante_uuid:
        raise Prohibido("Solo puedes consultar tu propia cuenta.")
    participante = repo_de(session, nid).obtener_por_uuid(participante_uuid)
    if participante is None or participante.id is None:
        raise NoEncontrado("Participante inexistente.")
    asientos = RepositorioLedgerSQLAlchemy(session, nid).listar(
        participante_id=participante.id
    )
    ahorros = Dinero.cero()
    for a in asientos:
        if a.fondo is TipoFondo.AHORRO:
            ahorros = (
                ahorros + a.monto if a.naturaleza is Naturaleza.CREDITO else ahorros - a.monto
            )
    return CuentaResponse(
        participante_uuid=participante_uuid,
        saldos=SaldosResponse(ahorros=ahorros.como_str()),
        asientos=[AsientoResponse.de_leido(a) for a in asientos],
    )


@router.post("/{participante_uuid}/estado", response_model=ParticipanteResponse)
def cambiar_estado(
    natillera_uuid: str,
    participante_uuid: str,
    datos: CambiarEstadoRequest,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ParticipanteResponse:
    uc = cambiar_estado_uc(session, bus, natillera_id_de(principal))
    p = uc.ejecutar(participante_uuid, datos.estado)
    return ParticipanteResponse.de_dominio(p)
