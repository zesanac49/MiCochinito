"""Value object `Documento` — identidad de un participante (doc 02 §3, RN-011).

Tipo (CC, CE, TI, PP) + número. Valida formato en construcción. La unicidad por
natillera la garantiza el constraint de BD; aquí solo se valida que esté bien
formado.
"""

from __future__ import annotations

import re
from enum import Enum

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


class TipoDocumento(str, Enum):
    CC = "CC"  # Cédula de ciudadanía
    CE = "CE"  # Cédula de extranjería
    TI = "TI"  # Tarjeta de identidad
    PP = "PP"  # Pasaporte


_SOLO_DIGITOS = re.compile(r"^\d{5,15}$")
_ALFANUMERICO = re.compile(r"^[A-Za-z0-9]{5,20}$")


class Documento:
    __slots__ = ("_tipo", "_numero")
    _tipo: TipoDocumento
    _numero: str

    def __init__(self, tipo: TipoDocumento, numero: str) -> None:
        if not isinstance(tipo, TipoDocumento):
            raise ErrorDeValidacionDeDominio("tipo de documento inválido.")
        numero = numero.strip()
        # CC/CE/TI son numéricos; PP admite alfanumérico.
        patron = _ALFANUMERICO if tipo is TipoDocumento.PP else _SOLO_DIGITOS
        if not patron.match(numero):
            raise ErrorDeValidacionDeDominio(
                "Número de documento con formato inválido para el tipo.",
                {"tipo": tipo.value, "numero": numero},
            )
        object.__setattr__(self, "_tipo", tipo)
        object.__setattr__(self, "_numero", numero)

    @property
    def tipo(self) -> TipoDocumento:
        return self._tipo

    @property
    def numero(self) -> str:
        return self._numero

    def __setattr__(self, name: str, value: object) -> None:  # pragma: no cover
        raise ErrorDeValidacionDeDominio("Documento es inmutable.")

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Documento):
            return NotImplemented
        return (self._tipo, self._numero) == (otro._tipo, otro._numero)

    def __hash__(self) -> int:
        return hash((self._tipo, self._numero))

    def __repr__(self) -> str:
        return f"Documento({self._tipo.value} {self._numero})"
