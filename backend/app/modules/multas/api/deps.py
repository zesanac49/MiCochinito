"""Composición del servicio de multas (doc 05 §2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
)
from app.modules.multas.application.servicios import ServicioMultas
from app.modules.multas.infrastructure.repositorios import (
    RepositorioCatalogoMultasSQLAlchemy,
    RepositorioMultasSQLAlchemy,
)
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.modules.participantes.infrastructure.repositorios import (
    RepositorioParticipantesSQLAlchemy,
)
from app.shared.infrastructure.auditoria import FabricaAuditoriaSQLAlchemy
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def servicio_multas(session: Session, bus: BusDeEventos, natillera_id: int) -> ServicioMultas:
    return ServicioMultas(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        ConsultaNatillera(RepositorioNatillerasSQLAlchemy(session)),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
        RepositorioMultasSQLAlchemy(session, natillera_id),
        RepositorioCatalogoMultasSQLAlchemy(session, natillera_id),
        FabricaContabilidadSQLAlchemy(session).para(natillera_id),
        FabricaAuditoriaSQLAlchemy(session),
    )


def repo_catalogo(session: Session, natillera_id: int) -> RepositorioCatalogoMultasSQLAlchemy:
    return RepositorioCatalogoMultasSQLAlchemy(session, natillera_id)


def repo_multas(session: Session, natillera_id: int) -> RepositorioMultasSQLAlchemy:
    return RepositorioMultasSQLAlchemy(session, natillera_id)
