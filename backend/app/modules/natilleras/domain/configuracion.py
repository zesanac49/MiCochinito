"""Configuración de la natillera (doc 02 §4.1, doc 04 §3.1, RF-102).

Cambios de configuración rigen hacia futuro (RN-020); el versionado histórico se
guarda en la capa de aplicación (tabla `configuraciones_historial`). La
estrategia de distribución se congela al entrar a PENDIENTE_LIQUIDACION (RN-073).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


class Periodicidad(str, Enum):
    MENSUAL = "MENSUAL"
    QUINCENAL = "QUINCENAL"
    SEMANAL = "SEMANAL"

    def cobros_por_mes(self) -> int:
        """Cuántos cobros/períodos genera cada mes (RF-301): mensual=1,
        quincenal=2, semanal=4."""
        return {"MENSUAL": 1, "QUINCENAL": 2, "SEMANAL": 4}[self.value]


class EstrategiaDistribucion(str, Enum):
    PARTES_IGUALES = "PARTES_IGUALES"
    PROPORCIONAL_AHORRO = "PROPORCIONAL_AHORRO"
    PROPORCIONAL_TIEMPO = "PROPORCIONAL_TIEMPO"


@dataclass(slots=True)
class Configuracion:
    """Parámetros configurables de una natillera. Validan en construcción."""

    valor_cuota: Dinero
    periodicidad_cuota: Periodicidad
    dia_limite_pago: int
    permite_aportes_extra: bool
    tasa_interes_base: Decimal
    tasa_interes_min: Decimal
    tasa_interes_max: Decimal
    max_prestamos_activos: int
    max_capital_vigente: Dinero
    estrategia_distribucion: EstrategiaDistribucion

    def __post_init__(self) -> None:
        if not self.valor_cuota.es_positivo():
            raise ErrorDeValidacionDeDominio("El valor de la cuota debe ser positivo.")
        if not (1 <= self.dia_limite_pago <= 31):
            raise ErrorDeValidacionDeDominio("dia_limite_pago debe estar entre 1 y 31.")
        for nombre, tasa in (
            ("tasa_interes_min", self.tasa_interes_min),
            ("tasa_interes_base", self.tasa_interes_base),
            ("tasa_interes_max", self.tasa_interes_max),
        ):
            if tasa <= 0:
                raise ErrorDeValidacionDeDominio(f"{nombre} debe ser positiva.")
        if not (self.tasa_interes_min <= self.tasa_interes_base <= self.tasa_interes_max):
            raise ErrorDeValidacionDeDominio(
                "Debe cumplirse tasa_min <= tasa_base <= tasa_max."
            )
        if self.max_prestamos_activos < 1:
            raise ErrorDeValidacionDeDominio("max_prestamos_activos debe ser >= 1.")
        if not self.max_capital_vigente.es_positivo():
            raise ErrorDeValidacionDeDominio("max_capital_vigente debe ser positivo.")
