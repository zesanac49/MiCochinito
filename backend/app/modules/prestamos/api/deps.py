"""Composición del servicio de préstamos (doc 05 §2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.eventbus import BusDeEventos
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
)
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.modules.participantes.infrastructure.repositorios import (
    RepositorioParticipantesSQLAlchemy,
)
from app.modules.prestamos.application.servicios import ServicioPrestamos
from app.modules.prestamos.infrastructure.repositorios import (
    RepositorioPrestamoPagosSQLAlchemy,
    RepositorioPrestamosSQLAlchemy,
)
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def servicio_prestamos(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> ServicioPrestamos:
    return ServicioPrestamos(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        ConsultaNatillera(RepositorioNatillerasSQLAlchemy(session)),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
        RepositorioPrestamosSQLAlchemy(session, natillera_id),
        RepositorioPrestamoPagosSQLAlchemy(session, natillera_id),
        FabricaContabilidadSQLAlchemy(session).para(natillera_id),
    )


def repo_prestamos(session: Session, natillera_id: int) -> RepositorioPrestamosSQLAlchemy:
    return RepositorioPrestamosSQLAlchemy(session, natillera_id)
