"""Composición del servicio de liquidación (doc 05 §2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.eventbus import BusDeEventos
from app.modules.actividades.infrastructure.repositorios import (
    RepositorioActividadesSQLAlchemy,
)
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
)
from app.modules.liquidacion.application.servicios import ServicioLiquidacion
from app.modules.liquidacion.infrastructure.repositorios import (
    RepositorioLiquidacionSQLAlchemy,
)
from app.modules.multas.infrastructure.repositorios import RepositorioMultasSQLAlchemy
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.modules.participantes.infrastructure.repositorios import (
    RepositorioParticipantesSQLAlchemy,
)
from app.modules.prestamos.infrastructure.repositorios import (
    RepositorioPrestamosSQLAlchemy,
)
from app.shared.infrastructure.auditoria import FabricaAuditoriaSQLAlchemy
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def servicio_liquidacion(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> ServicioLiquidacion:
    return ServicioLiquidacion(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        ConsultaNatillera(RepositorioNatillerasSQLAlchemy(session)),
        RepositorioLiquidacionSQLAlchemy(session, natillera_id),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
        RepositorioPrestamosSQLAlchemy(session, natillera_id),
        RepositorioMultasSQLAlchemy(session, natillera_id),
        RepositorioActividadesSQLAlchemy(session, natillera_id),
        FabricaContabilidadSQLAlchemy(session).para(natillera_id),
        FabricaAuditoriaSQLAlchemy(session),
    )


def repo_participantes(session: Session, natillera_id: int) -> RepositorioParticipantesSQLAlchemy:
    return RepositorioParticipantesSQLAlchemy(session, natillera_id)
