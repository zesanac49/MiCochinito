"""Value object `Periodo` — año + mes (doc 02 §3).

Representa un período mensual del ciclo de la natillera. La validación de que
el período cae dentro del ciclo concreto se hace en el agregado Natillera (que
conoce sus fechas); aquí solo se garantiza un año/mes bien formado.
"""

from __future__ import annotations

from typing import Final

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio

_ANIO_MIN: Final[int] = 2000
_ANIO_MAX: Final[int] = 2100


class Periodo:
    """Período mensual (año, mes) inmutable, con orden natural."""

    __slots__ = ("_anio", "_mes")
    _anio: int
    _mes: int

    def __init__(self, anio: int, mes: int) -> None:
        es_entero_puro = (
            isinstance(anio, int)
            and isinstance(mes, int)
            and not isinstance(anio, bool)
            and not isinstance(mes, bool)
        )
        if not es_entero_puro:
            raise ErrorDeValidacionDeDominio("año y mes deben ser enteros.")
        if not (_ANIO_MIN <= anio <= _ANIO_MAX):
            raise ErrorDeValidacionDeDominio(
                "Año fuera de rango.", {"anio": anio, "min": _ANIO_MIN, "max": _ANIO_MAX}
            )
        if not (1 <= mes <= 12):
            raise ErrorDeValidacionDeDominio("Mes debe estar entre 1 y 12.", {"mes": mes})
        object.__setattr__(self, "_anio", anio)
        object.__setattr__(self, "_mes", mes)

    @property
    def anio(self) -> int:
        return self._anio

    @property
    def mes(self) -> int:
        return self._mes

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorDeValidacionDeDominio("Periodo es inmutable.")

    def _orden(self) -> int:
        return self._anio * 12 + (self._mes - 1)

    def siguiente(self) -> Periodo:
        if self._mes == 12:
            return Periodo(self._anio + 1, 1)
        return Periodo(self._anio, self._mes + 1)

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Periodo):
            return NotImplemented
        return (self._anio, self._mes) == (otro._anio, otro._mes)

    def __lt__(self, otro: Periodo) -> bool:
        return self._orden() < otro._orden()

    def __le__(self, otro: Periodo) -> bool:
        return self._orden() <= otro._orden()

    def __hash__(self) -> int:
        return hash((self._anio, self._mes))

    def __repr__(self) -> str:
        return f"Periodo({self._anio:04d}-{self._mes:02d})"

    def __str__(self) -> str:
        return f"{self._anio:04d}-{self._mes:02d}"
