"""Puerto de auditoría de acciones (transversal, RN-062, INV-13)."""

from __future__ import annotations

from typing import Protocol


class RegistroAuditoria(Protocol):
    """Registra una acción no contable auditada. Ligado a un tenant."""

    def registrar(
        self,
        usuario_id: int,
        accion: str,
        entidad_tipo: str,
        entidad_id: int | None = None,
        detalle: dict[str, object] | None = None,
    ) -> None: ...


class FabricaAuditoria(Protocol):
    """Construye un registro de auditoría ligado a un tenant."""

    def para(self, natillera_id: int) -> RegistroAuditoria: ...
