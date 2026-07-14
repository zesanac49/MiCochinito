"""Value object `TasaInteres` (TEC-04, doc 02 §3).

Porcentaje mensual como `Decimal` (jamás float). 0 < tasa ≤ tope configurado.
El tope se valida en construcción cuando se provee (p. ej. límites de la
configuración de la natillera, RN-031).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio

_CIEN = Decimal("100")


class TasaInteres:
    """Tasa de interés mensual (porcentaje). Inmutable, igualdad por valor."""

    __slots__ = ("_porcentaje",)
    _porcentaje: Decimal

    def __init__(self, porcentaje: Decimal | int | str, tope: Decimal | None = None) -> None:
        if isinstance(porcentaje, bool | float):
            raise ErrorDeValidacionDeDominio(
                "La tasa debe ser Decimal, int o str; nunca float (TEC-01)."
            )
        try:
            valor = Decimal(porcentaje)
        except (InvalidOperation, ValueError) as exc:
            raise ErrorDeValidacionDeDominio("Tasa inválida.", {"valor": str(porcentaje)}) from exc
        if not valor.is_finite() or valor <= 0:
            raise ErrorDeValidacionDeDominio("La tasa debe ser positiva.", {"valor": str(valor)})
        if tope is not None and valor > tope:
            raise ErrorDeValidacionDeDominio(
                "La tasa excede el tope configurado.",
                {"tasa": str(valor), "tope": str(tope)},
            )
        object.__setattr__(self, "_porcentaje", valor)

    @property
    def porcentaje(self) -> Decimal:
        return self._porcentaje

    @property
    def fraccion(self) -> Decimal:
        """Tasa como fracción (p. ej. 2.5% -> 0.025) para multiplicar montos."""
        return self._porcentaje / _CIEN

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorDeValidacionDeDominio("TasaInteres es inmutable.")

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, TasaInteres):
            return NotImplemented
        return self._porcentaje == otro._porcentaje

    def __hash__(self) -> int:
        return hash(self._porcentaje)

    def __repr__(self) -> str:
        return f"TasaInteres({self._porcentaje}%)"
