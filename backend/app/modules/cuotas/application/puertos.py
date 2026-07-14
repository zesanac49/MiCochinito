"""Puertos del módulo cuotas (doc 05 §4). No importan infraestructura."""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from app.modules.cuotas.application.dtos import CuotaCreada


class RepositorioCuotas(Protocol):
    def existe_pagada(self, participante_id: int, periodo_id: int) -> bool: ...

    def crear_pagada(
        self, participante_id: int, periodo_id: int, valor: Decimal
    ) -> CuotaCreada: ...

    def enlazar_asiento(self, cuota_id: int, asiento_id: int | None) -> None: ...
