"""DTOs del módulo cuotas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CuotaCreada:
    id: int
    uuid: str


@dataclass(frozen=True, slots=True)
class ItemLoteResultado:
    participante_uuid: str
    periodo_uuid: str
    estado: str  # "PAGADO" | "YA_PAGADO" | "NO_ENCONTRADO"
    asiento_uuid: str | None = None


@dataclass(frozen=True, slots=True)
class ResumenLote:
    items: list[ItemLoteResultado]
    cantidad_pagados: int
    total_recaudado: str  # string decimal (TEC-01)
