"""Composición de casos de uso de natilleras (doc 05 §2)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import obtener_bus, obtener_session
from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
    GeneradorPeriodosSQLAlchemy,
)
from app.modules.natilleras.application.casos_uso import (
    ConfigurarNatillera,
    CrearNatillera,
    TransicionarEstado,
)
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.shared.infrastructure.auditoria import FabricaAuditoriaSQLAlchemy
from app.shared.infrastructure.membresias import AsignadorMembresiaSQLAlchemy
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def obtener_repo(session: Session = Depends(obtener_session)) -> RepositorioNatillerasSQLAlchemy:
    return RepositorioNatillerasSQLAlchemy(session)


def uc_crear(
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> CrearNatillera:
    return CrearNatillera(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioNatillerasSQLAlchemy(session),
        FabricaContabilidadSQLAlchemy(session),
        AsignadorMembresiaSQLAlchemy(session),
    )


def uc_configurar(
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> ConfigurarNatillera:
    return ConfigurarNatillera(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioNatillerasSQLAlchemy(session),
        FabricaAuditoriaSQLAlchemy(session),
    )


def uc_transicionar(
    session: Session = Depends(obtener_session),
    bus: BusDeEventos = Depends(obtener_bus),
) -> TransicionarEstado:
    return TransicionarEstado(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioNatillerasSQLAlchemy(session),
        FabricaAuditoriaSQLAlchemy(session),
        GeneradorPeriodosSQLAlchemy(session),
    )
