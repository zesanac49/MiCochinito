"""Value object `NumeroPolla` (TEC-04, doc 02 §3).

Número de participación en una polla: entero entre 1 y la cantidad configurada.
"""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


class NumeroPolla:
    __slots__ = ("_valor",)
    _valor: int

    def __init__(self, valor: int, cantidad: int) -> None:
        if isinstance(valor, bool) or not isinstance(valor, int):
            raise ErrorDeValidacionDeDominio("El número de polla debe ser entero.")
        if not (1 <= valor <= cantidad):
            raise ErrorDeValidacionDeDominio(
                "Número de polla fuera de rango.",
                {"numero": valor, "min": 1, "max": cantidad},
            )
        object.__setattr__(self, "_valor", valor)

    @property
    def valor(self) -> int:
        return self._valor

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorDeValidacionDeDominio("NumeroPolla es inmutable.")

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, NumeroPolla):
            return NotImplemented
        return self._valor == otro._valor

    def __hash__(self) -> int:
        return hash(self._valor)

    def __repr__(self) -> str:
        return f"NumeroPolla({self._valor})"
