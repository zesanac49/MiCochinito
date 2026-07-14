"""Agregado `Multa` (doc 02 §4.6, RN-050/051/052).

La multa impuesta es una cuenta por cobrar; solo su pago genera rentabilidad
(INV-10). Estados: `IMPUESTA → PAGADA | ANULADA`. Una multa pagada no se anula
(se revierte con RF-305).
"""

from __future__ import annotations

from enum import Enum

from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida


class EstadoMulta(str, Enum):
    IMPUESTA = "IMPUESTA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"


class Multa(RaizDeAgregado):
    def __init__(
        self,
        participante_id: int,
        valor: Dinero,
        motivo: str,
        estado: EstadoMulta = EstadoMulta.IMPUESTA,
        catalogo_multa_id: int | None = None,
        origen_tipo: str | None = None,
        origen_id: int | None = None,
        justificacion_anulacion: str | None = None,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        if not valor.es_positivo():
            raise ErrorDeValidacionDeDominio("El valor de la multa debe ser positivo.")
        if not motivo.strip():
            raise ErrorDeValidacionDeDominio("La multa requiere motivo.")
        self._participante_id = participante_id
        self._valor = valor
        self._motivo = motivo
        self._estado = estado
        self._catalogo_multa_id = catalogo_multa_id
        self._origen_tipo = origen_tipo
        self._origen_id = origen_id
        self._justificacion_anulacion = justificacion_anulacion
        self.uuid = uuid

    @classmethod
    def imponer(
        cls,
        participante_id: int,
        valor: Dinero,
        motivo: str,
        catalogo_multa_id: int | None = None,
        origen_tipo: str | None = None,
        origen_id: int | None = None,
    ) -> Multa:
        return cls(
            participante_id,
            valor,
            motivo,
            catalogo_multa_id=catalogo_multa_id,
            origen_tipo=origen_tipo,
            origen_id=origen_id,
        )

    @property
    def participante_id(self) -> int:
        return self._participante_id

    @property
    def valor(self) -> Dinero:
        return self._valor

    @property
    def motivo(self) -> str:
        return self._motivo

    @property
    def estado(self) -> EstadoMulta:
        return self._estado

    @property
    def catalogo_multa_id(self) -> int | None:
        return self._catalogo_multa_id

    @property
    def justificacion_anulacion(self) -> str | None:
        return self._justificacion_anulacion

    def pagar(self) -> None:
        if self._estado is not EstadoMulta.IMPUESTA:
            raise TransicionInvalida(
                "Solo una multa impuesta puede pagarse.", {"estado": self._estado.value}
            )
        self._estado = EstadoMulta.PAGADA

    def anular(self, justificacion: str) -> None:
        if self._estado is not EstadoMulta.IMPUESTA:
            raise TransicionInvalida(
                "Una multa pagada o ya anulada no puede anularse (revertir con RF-305).",
                {"estado": self._estado.value},
            )
        if not justificacion.strip():
            raise ErrorDeValidacionDeDominio("La anulación requiere justificación.")
        self._estado = EstadoMulta.ANULADA
        self._justificacion_anulacion = justificacion
