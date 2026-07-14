"""Dominio mínimo de cuotas (doc 04 §3.5)."""

from __future__ import annotations

from enum import Enum


class EstadoCuota(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA = "PAGADA"
    REVERTIDA = "REVERTIDA"
