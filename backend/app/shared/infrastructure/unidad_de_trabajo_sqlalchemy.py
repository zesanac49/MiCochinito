"""Implementación SQLAlchemy del Unit of Work (doc 05 §4).

Traduce los puntos abstractos del puerto (`_flush`, `_commit_transaccion`,
`rollback`) a operaciones sobre una `Session`. La publicación de eventos y el
registro de agregados los hereda de la clase base (agnóstica de infraestructura).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.eventbus import BusDeEventos
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo


class UnidadDeTrabajoSQLAlchemy(UnidadDeTrabajo):
    def __init__(self, session: Session, bus: BusDeEventos) -> None:
        super().__init__(bus)
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def _flush(self) -> None:
        self._session.flush()

    def _commit_transaccion(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
