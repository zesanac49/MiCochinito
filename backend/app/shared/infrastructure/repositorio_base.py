"""Repositorio base con filtro de tenant obligatorio (TEC-02, doc 05 §4).

Todo query de negocio parte de `natillera_id`: el constructor EXIGE el tenant
del contexto (resuelto por la dependencia de FastAPI, doc 05 §6) y jamás se
acepta del body. Ningún método de negocio puede omitir el filtro: `_select_tenant`
es el único punto de construcción de queries y ya lo aplica.

El TypeVar se acota a `ModeloTenant`, que garantiza (a nivel de tipos) que el
modelo tiene `natillera_id` y `uuid`.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.shared.infrastructure.db import ModeloTenant

TModelo = TypeVar("TModelo", bound=ModeloTenant)


class RepositorioBaseConTenant(Generic[TModelo]):
    """Base de repositorios de entidades multi-tenant.

    Subclase típica:
        class RepositorioParticipantes(RepositorioBaseConTenant[ParticipanteModel]):
            modelo = ParticipanteModel
    """

    modelo: type[TModelo]

    def __init__(self, session: Session, natillera_id: int) -> None:
        if natillera_id is None:  # defensa explícita: el tenant es obligatorio
            raise ValueError("natillera_id es obligatorio (TEC-02).")
        self._session = session
        self._natillera_id = natillera_id

    @property
    def natillera_id(self) -> int:
        return self._natillera_id

    def _select_tenant(self) -> Select[tuple[TModelo]]:
        """Único constructor de queries: siempre filtrado por tenant."""
        return select(self.modelo).where(self.modelo.natillera_id == self._natillera_id)

    def agregar(self, entidad: TModelo) -> TModelo:
        # Blindaje: fuerza el tenant del contexto, ignorando cualquier valor
        # que traiga la entidad (nunca se confía en el body).
        entidad.natillera_id = self._natillera_id
        self._session.add(entidad)
        return entidad

    def obtener_por_uuid(self, uuid: str) -> TModelo | None:
        stmt = self._select_tenant().where(self.modelo.uuid == uuid)
        return self._session.scalars(stmt).first()

    def listar(self) -> list[TModelo]:
        return list(self._session.scalars(self._select_tenant()).all())
