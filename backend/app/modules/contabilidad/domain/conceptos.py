"""Enumeraciones del núcleo contable (doc 02 §5, doc 04 §3.4).

`ConceptoContable` es cerrado: los conceptos futuros tras feature flag (RN-091,
donaciones/rendimientos) NO se incluyen aquí hasta que se implementen. Agregar
un concepto es una decisión de negocio (extiende la matriz, doc 02 §5).
"""

from __future__ import annotations

from enum import Enum


class TipoFondo(str, Enum):
    """Solo existen dos fondos por natillera (RN-001, INV-01)."""

    AHORRO = "AHORRO"
    RENTABILIDAD = "RENTABILIDAD"


class Naturaleza(str, Enum):
    """Naturaleza contable de un asiento."""

    DEBITO = "DEBITO"
    CREDITO = "CREDITO"


class ConceptoContable(str, Enum):
    """Conceptos permitidos del ledger (doc 02 §5, doc 04 §3.4)."""

    CUOTA_AHORRO = "CUOTA_AHORRO"
    APORTE_EXTRAORDINARIO = "APORTE_EXTRAORDINARIO"
    DESEMBOLSO_PRESTAMO = "DESEMBOLSO_PRESTAMO"
    RETORNO_CAPITAL = "RETORNO_CAPITAL"
    INTERES_PAGADO = "INTERES_PAGADO"
    UTILIDAD_ACTIVIDAD = "UTILIDAD_ACTIVIDAD"
    PERDIDA_ACTIVIDAD = "PERDIDA_ACTIVIDAD"
    MULTA_PAGADA = "MULTA_PAGADA"
    DEVOLUCION_AHORRO = "DEVOLUCION_AHORRO"
    DISTRIBUCION_RENTABILIDAD = "DISTRIBUCION_RENTABILIDAD"
    REVERSION = "REVERSION"
