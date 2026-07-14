"""Endpoints de contabilidad: asientos y fondos del tenant (RF-104/803, doc 07)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import Principal, Rol, require_rol
from app.core.deps import obtener_session
from app.core.errors import SinMembresia
from app.modules.contabilidad.api.schemas import (
    AsientoResponse,
    FondoResponse,
    PeriodoResponse,
    ReconciliacionResponse,
    ReversionRequest,
)
from app.modules.contabilidad.application.dtos import SaldoFondo
from app.modules.contabilidad.application.reconciliacion import ServicioReconciliacion
from app.modules.contabilidad.domain.conceptos import ConceptoContable, TipoFondo
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
    RepositorioFondosSQLAlchemy,
    RepositorioLedgerSQLAlchemy,
    RepositorioPeriodosSQLAlchemy,
)
from app.shared.infrastructure.auditoria import FabricaAuditoriaSQLAlchemy

router = APIRouter(prefix="/api/v1/natilleras/{natillera_uuid}", tags=["contabilidad"])

_ADMIN = require_rol(Rol.ADMINISTRADOR)
_ADMIN_SUP = require_rol(Rol.ADMINISTRADOR, Rol.SUPERVISOR)


def _natillera_id(principal: Principal) -> int:
    if principal.natillera_id is None:
        raise SinMembresia("Sin membresía en esta natillera.")
    return principal.natillera_id


@router.get("/asientos", response_model=list[AsientoResponse])
def listar_asientos(
    natillera_uuid: str,
    fondo: TipoFondo | None = None,
    concepto: ConceptoContable | None = None,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[AsientoResponse]:
    repo = RepositorioLedgerSQLAlchemy(session, _natillera_id(principal))
    asientos = repo.listar(fondo=fondo, concepto=concepto)
    return [AsientoResponse.de_leido(a) for a in asientos]


@router.get("/fondos", response_model=list[FondoResponse])
def listar_fondos(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[FondoResponse]:
    repo = RepositorioFondosSQLAlchemy(session, _natillera_id(principal))
    return [
        FondoResponse.de_saldo(SaldoFondo(tipo, repo.saldo(tipo)))
        for tipo in (TipoFondo.AHORRO, TipoFondo.RENTABILIDAD)
    ]


@router.get("/dashboard")
def dashboard(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    """Saldos de fondos + rentabilidad por fuente (RF-104/901)."""
    nid = _natillera_id(principal)
    fondos = RepositorioFondosSQLAlchemy(session, nid)
    ledger = RepositorioLedgerSQLAlchemy(session, nid)
    return {
        "fondos": [
            {"tipo": t.value, "saldo": fondos.saldo(t).como_str()}
            for t in (TipoFondo.AHORRO, TipoFondo.RENTABILIDAD)
        ],
        "rentabilidad_por_fuente": {
            k: v.como_str() for k, v in ledger.rentabilidad_por_fuente().items()
        },
    }


@router.get("/periodos", response_model=list[PeriodoResponse])
def listar_periodos(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> list[PeriodoResponse]:
    repo = RepositorioPeriodosSQLAlchemy(session, _natillera_id(principal))
    return [PeriodoResponse.de_modelo(m) for m in repo.listar()]


@router.post(
    "/asientos/{asiento_uuid}/reversion",
    response_model=AsientoResponse,
    status_code=201,
)
def revertir_asiento(
    natillera_uuid: str,
    asiento_uuid: str,
    datos: ReversionRequest,
    principal: Principal = Depends(_ADMIN_SUP),
    session: Session = Depends(obtener_session),
) -> AsientoResponse:
    nid = _natillera_id(principal)
    autor = principal.usuario_id or 0
    svc = FabricaContabilidadSQLAlchemy(session).para(nid)
    leido = svc.revertir(asiento_uuid, datos.motivo, autor)
    FabricaAuditoriaSQLAlchemy(session).para(nid).registrar(
        autor, "REVERSION", "ASIENTO", None, {"asiento": asiento_uuid, "motivo": datos.motivo}
    )
    session.commit()
    return AsientoResponse.de_leido(leido)


@router.post("/reconciliacion", response_model=ReconciliacionResponse)
def reconciliar(
    natillera_uuid: str,
    principal: Principal = Depends(_ADMIN),
    session: Session = Depends(obtener_session),
) -> ReconciliacionResponse:
    nid = _natillera_id(principal)
    servicio = ServicioReconciliacion(
        RepositorioFondosSQLAlchemy(session, nid),
        FabricaAuditoriaSQLAlchemy(session).para(nid),
    )
    reporte = servicio.reconciliar(principal.usuario_id or 0)
    session.commit()  # persiste la auditoría de descuadre si la hubo
    return ReconciliacionResponse.de_reporte(reporte)
