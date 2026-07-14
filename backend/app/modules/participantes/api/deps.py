"""Constructores de casos de uso de participantes (composición, doc 05 §2)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.core.errors import SinMembresia
from app.core.eventbus import BusDeEventos
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.natilleras.infrastructure.repositorios import (
    RepositorioNatillerasSQLAlchemy,
)
from app.modules.participantes.application.casos_uso import (
    CambiarEstadoParticipante,
    EditarContacto,
    InscribirParticipante,
)
from app.modules.participantes.infrastructure.repositorios import (
    RepositorioParticipantesSQLAlchemy,
)
from app.shared.infrastructure.unidad_de_trabajo_sqlalchemy import (
    UnidadDeTrabajoSQLAlchemy,
)


def natillera_id_de(principal: Principal) -> int:
    if principal.natillera_id is None:
        raise SinMembresia("Sin membresía en esta natillera.")
    return principal.natillera_id


def repo_de(session: Session, natillera_id: int) -> RepositorioParticipantesSQLAlchemy:
    return RepositorioParticipantesSQLAlchemy(session, natillera_id)


def inscribir_uc(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> InscribirParticipante:
    return InscribirParticipante(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
        ConsultaNatillera(RepositorioNatillerasSQLAlchemy(session)),
    )


def cambiar_estado_uc(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> CambiarEstadoParticipante:
    return CambiarEstadoParticipante(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
    )


def editar_contacto_uc(
    session: Session, bus: BusDeEventos, natillera_id: int
) -> EditarContacto:
    return EditarContacto(
        UnidadDeTrabajoSQLAlchemy(session, bus),
        RepositorioParticipantesSQLAlchemy(session, natillera_id),
    )
