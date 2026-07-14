"""Composición del servicio de cuotas (doc 05 §2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
    RepositorioPeriodosSQLAlchemy,
)
from app.modules.cuotas.application.servicios import ServicioCuotas
from app.modules.cuotas.infrastructure.repositorios import RepositorioCuotasSQLAlchemy
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.modules.participantes.infrastructure.repositorios import (
    RepositorioParticipantesSQLAlchemy,
)
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def servicio_cuotas(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> ServicioCuotas:
    return ServicioCuotas(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        ConsultaNatillera(RepositorioNatillerasSQLAlchemy(session)),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
        RepositorioPeriodosSQLAlchemy(session, natillera_id),
        RepositorioCuotasSQLAlchemy(session, natillera_id),
        FabricaContabilidadSQLAlchemy(session).para(natillera_id),
    )
