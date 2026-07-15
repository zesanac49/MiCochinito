"""Puertos del módulo liquidación (doc 05 §4)."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from app.modules.liquidacion.domain.liquidacion import Liquidacion
from app.shared.domain.dinero import Dinero


class ProveedorMoraCuotas(Protocol):
    """Calcula la mora de cuotas de ahorro atrasadas de un participante (3B)."""

    def mora_pendiente_de(
        self, participante_id: int, valor_mora: Dinero, hoy: date
    ) -> Dinero: ...


class RepositorioLiquidacion(Protocol):
    def obtener_por_natillera(self, natillera_id: int) -> Liquidacion | None: ...

    def agregar(self, liquidacion: Liquidacion) -> Liquidacion: ...

    def guardar(self, liquidacion: Liquidacion) -> None: ...

    def marcar_confirmada(self, liquidacion_id: int, usuario_id: int) -> None: ...

    def registrar_decision(
        self,
        liquidacion_id: int,
        tipo_bloqueo: str,
        origen_tipo: str,
        origen_id: int,
        decision: str,
        decidido_por: int,
    ) -> None: ...

    def claves_decididas(self, liquidacion_id: int) -> set[tuple[str, str, int]]: ...

    def marcar_entregado(
        self, liquidacion_id: int, participante_id: int, usuario_id: int
    ) -> bool: ...
