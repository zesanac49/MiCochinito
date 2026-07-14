"""Value object `Dinero` — el guardián monetario del sistema (TEC-01, TEC-04).

Reglas innegociables:
- El monto es SIEMPRE `decimal.Decimal` con 2 decimales. Nunca `float`.
- Prohibida la construcción desde `float` (fuente de errores de redondeo).
- Moneda fija COP (multi-moneda fuera de alcance, doc 00 §8).
- Inmutable, con igualdad por valor.
- Las operaciones aritméticas solo ocurren entre `Dinero` (suma/resta) o
  contra un escalar entero/Decimal (multiplicación/división por cantidades).

`Dinero` admite montos negativos: son necesarios para cálculos intermedios
(p. ej. utilidad negativa de una actividad, RN-042a). La regla de "saldos no
negativos" (RN-007) se valida en los agregados de fondo, no aquí.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Final

from app.shared.domain.excepciones import ErrorMonetario

MONEDA: Final[str] = "COP"
_CENTAVO: Final[Decimal] = Decimal("0.01")


class Dinero:
    """Cantidad monetaria en COP con 2 decimales exactos."""

    __slots__ = ("_monto",)
    _monto: Decimal

    def __init__(self, monto: Decimal | int | str) -> None:
        if isinstance(monto, bool):
            # bool es subclase de int; rechazarlo evita True/False como monto.
            raise ErrorMonetario("Un booleano no es un monto válido.")
        if isinstance(monto, float):
            raise ErrorMonetario(
                "Prohibido construir Dinero desde float (TEC-01). "
                "Usa str, int o Decimal.",
                {"tipo_recibido": "float", "valor": repr(monto)},
            )
        if not isinstance(monto, Decimal | int | str):
            raise ErrorMonetario(
                "Dinero solo acepta Decimal, int o str.",
                {"tipo_recibido": type(monto).__name__},
            )
        try:
            valor = Decimal(monto)
        except (InvalidOperation, ValueError) as exc:
            raise ErrorMonetario(
                "Valor monetario inválido.", {"valor": str(monto)}
            ) from exc
        if not valor.is_finite():
            raise ErrorMonetario("El monto debe ser finito.", {"valor": str(monto)})
        object.__setattr__(self, "_monto", valor.quantize(_CENTAVO, rounding=ROUND_HALF_UP))

    # --- Fábricas -----------------------------------------------------------
    @classmethod
    def cero(cls) -> Dinero:
        return cls(Decimal("0"))

    # --- Acceso -------------------------------------------------------------
    @property
    def monto(self) -> Decimal:
        return self._monto

    @property
    def moneda(self) -> str:
        return MONEDA

    def es_cero(self) -> bool:
        return self._monto == 0

    def es_positivo(self) -> bool:
        return self._monto > 0

    def es_negativo(self) -> bool:
        return self._monto < 0

    # --- Inmutabilidad ------------------------------------------------------
    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorMonetario("Dinero es inmutable.")

    def __delattr__(self, name: str) -> None:  # pragma: no cover
        raise ErrorMonetario("Dinero es inmutable.")

    # --- Aritmética entre Dinero -------------------------------------------
    def _exigir_dinero(self, otro: object) -> Dinero:
        if not isinstance(otro, Dinero):
            raise ErrorMonetario(
                "Solo se puede operar Dinero con Dinero.",
                {"tipo_recibido": type(otro).__name__},
            )
        return otro

    def __add__(self, otro: object) -> Dinero:
        o = self._exigir_dinero(otro)
        return Dinero(self._monto + o._monto)

    def __sub__(self, otro: object) -> Dinero:
        o = self._exigir_dinero(otro)
        return Dinero(self._monto - o._monto)

    def __neg__(self) -> Dinero:
        return Dinero(-self._monto)

    def __abs__(self) -> Dinero:
        return Dinero(abs(self._monto))

    # --- Escalado por cantidades -------------------------------------------
    def _exigir_escalar(self, factor: object) -> Decimal:
        if isinstance(factor, bool | float):
            raise ErrorMonetario(
                "El factor debe ser int o Decimal, nunca float ni bool.",
                {"tipo_recibido": type(factor).__name__},
            )
        if not isinstance(factor, int | Decimal):
            raise ErrorMonetario(
                "El factor debe ser int o Decimal.",
                {"tipo_recibido": type(factor).__name__},
            )
        return Decimal(factor)

    def multiplicado_por(self, factor: int | Decimal) -> Dinero:
        """Escala el monto por una cantidad (p. ej. valor_numero × cantidad)."""
        return Dinero(self._monto * self._exigir_escalar(factor))

    def __mul__(self, factor: object) -> Dinero:
        return self.multiplicado_por(self._exigir_escalar(factor))

    __rmul__ = __mul__

    # --- Comparaciones (solo entre Dinero) ---------------------------------
    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Dinero):
            return NotImplemented
        return self._monto == otro._monto

    def __lt__(self, otro: object) -> bool:
        return self._monto < self._exigir_dinero(otro)._monto

    def __le__(self, otro: object) -> bool:
        return self._monto <= self._exigir_dinero(otro)._monto

    def __gt__(self, otro: object) -> bool:
        return self._monto > self._exigir_dinero(otro)._monto

    def __ge__(self, otro: object) -> bool:
        return self._monto >= self._exigir_dinero(otro)._monto

    def __hash__(self) -> int:
        return hash((MONEDA, self._monto))

    # --- Serialización ------------------------------------------------------
    def como_str(self) -> str:
        """Representación canónica para la API (doc 07 §1): string decimal."""
        return f"{self._monto:.2f}"

    def __repr__(self) -> str:
        return f"Dinero('{self._monto:.2f}' {MONEDA})"

    def __str__(self) -> str:
        return self.como_str()
