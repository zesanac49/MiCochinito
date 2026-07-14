"""Jerarquía base de excepciones de dominio (doc 05 §7).

El dominio es Python puro: estas excepciones no conocen HTTP. La capa `api`
las mapea a códigos del catálogo cerrado (doc 07 §4).
"""

from __future__ import annotations


class ErrorDeDominio(Exception):
    """Raíz de todos los errores de negocio.

    Atributo `codigo`: identificador estable mapeado a HTTP en la capa api
    (doc 07 §4). Las subclases lo fijan.
    """

    codigo: str = "ERROR_DE_DOMINIO"

    def __init__(self, mensaje: str, detalle: dict[str, object] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle: dict[str, object] = detalle or {}


class ErrorMonetario(ErrorDeDominio):
    """Uso indebido del value object `Dinero` (TEC-01)."""

    codigo = "ERROR_MONETARIO"


class ErrorDeValidacionDeDominio(ErrorDeDominio):
    """Construcción inválida de un value object o entidad."""

    codigo = "VALIDACION_DE_DOMINIO"


class TransicionInvalida(ErrorDeDominio):
    """Transición de estado no permitida por una máquina de estados
    (RN-080/032/043/051)."""

    codigo = "TRANSICION_INVALIDA"
