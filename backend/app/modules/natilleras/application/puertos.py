"""Puertos del módulo natilleras (doc 05 §4)."""

from __future__ import annotations

from typing import Protocol

from app.modules.natilleras.domain.natillera import Natillera


class RepositorioNatilleras(Protocol):
    def agregar(self, natillera: Natillera) -> Natillera: ...

    def obtener_por_uuid(self, uuid: str) -> Natillera | None: ...

    def guardar(self, natillera: Natillera) -> None:
        """Persiste cambios de estado/configuración de una natillera existente."""
        ...

    def registrar_historial(
        self, natillera_id: int, snapshot: dict[str, object], autor_id: int
    ) -> None:
        """Guarda un snapshot de configuración (RN-020)."""
        ...

    def listar(self) -> list[Natillera]: ...

    def listar_de_usuario(self, usuario_id: int) -> list[Natillera]:
        """Natilleras donde el usuario tiene membresía (RNF-02)."""
        ...
