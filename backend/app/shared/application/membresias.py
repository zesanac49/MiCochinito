"""Puerto de asignación de membresías usuario-natillera (RF-1002)."""

from __future__ import annotations

from typing import Protocol


class AsignadorMembresia(Protocol):
    def asignar(self, usuario_id: int, natillera_id: int, rol: str) -> None:
        """Crea (si no existe) la membresía del usuario en la natillera con el rol."""
        ...
