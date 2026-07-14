"""Eventos de dominio de la natillera (doc 02 §6)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.natilleras.domain.estados import EstadoNatillera
from app.shared.domain.eventos import EventoDeDominio


@dataclass(frozen=True, slots=True)
class NatilleraTransicionada(EventoDeDominio):
    """La natillera avanzó de estado (RN-080). Consumido por auditoría/futuros."""

    desde: EstadoNatillera
    hacia: EstadoNatillera
