"""Puertos del módulo actividades (doc 05 §4)."""

from __future__ import annotations

from typing import Protocol

from app.modules.actividades.domain.actividad import Actividad
from app.modules.actividades.domain.estados import EstadoActividad, TipoActividad


class RepositorioActividades(Protocol):
    def agregar(self, actividad: Actividad) -> Actividad: ...

    def guardar(self, actividad: Actividad) -> None: ...

    def obtener_por_uuid(self, uuid: str) -> Actividad | None: ...

    def listar(
        self,
        *,
        periodo_id: int | None = None,
        tipo: TipoActividad | None = None,
        estado: EstadoActividad | None = None,
    ) -> list[Actividad]: ...

    def ids_no_cerradas(self) -> list[int]:
        """Ids de actividades no CERRADA (bloqueos de liquidación)."""
        ...
