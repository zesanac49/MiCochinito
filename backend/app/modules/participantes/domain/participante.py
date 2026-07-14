"""Agregado `Participante` (doc 02 §4.2, RN-010/011/012).

Estados `Activo|Suspendido|Retirado`. Nunca se elimina físicamente (RN-012): un
retirado conserva su historial. El estado de cuenta NO es parte de este agregado
(es una proyección del ledger, módulo contabilidad).
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.documento import Documento
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida


class EstadoParticipante(str, Enum):
    ACTIVO = "ACTIVO"
    SUSPENDIDO = "SUSPENDIDO"
    RETIRADO = "RETIRADO"


# Transiciones válidas de estado del participante (RN-012).
_TRANSICIONES: dict[EstadoParticipante, frozenset[EstadoParticipante]] = {
    EstadoParticipante.ACTIVO: frozenset(
        {EstadoParticipante.SUSPENDIDO, EstadoParticipante.RETIRADO}
    ),
    EstadoParticipante.SUSPENDIDO: frozenset(
        {EstadoParticipante.ACTIVO, EstadoParticipante.RETIRADO}
    ),
    EstadoParticipante.RETIRADO: frozenset(),  # terminal
}


class Participante(RaizDeAgregado):
    def __init__(
        self,
        nombre: str,
        documento: Documento,
        fecha_ingreso: date,
        estado: EstadoParticipante = EstadoParticipante.ACTIVO,
        telefono: str | None = None,
        direccion: str | None = None,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        if not nombre.strip():
            raise ErrorDeValidacionDeDominio("El participante requiere nombre.")
        self._nombre = nombre
        self._documento = documento
        self._fecha_ingreso = fecha_ingreso
        self._estado = estado
        self._telefono = telefono
        self._direccion = direccion
        self.uuid = uuid

    @classmethod
    def inscribir(
        cls,
        nombre: str,
        documento: Documento,
        fecha_ingreso: date,
        telefono: str | None = None,
        direccion: str | None = None,
    ) -> Participante:
        return cls(nombre, documento, fecha_ingreso, telefono=telefono, direccion=direccion)

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def documento(self) -> Documento:
        return self._documento

    @property
    def fecha_ingreso(self) -> date:
        return self._fecha_ingreso

    @property
    def estado(self) -> EstadoParticipante:
        return self._estado

    @property
    def telefono(self) -> str | None:
        return self._telefono

    @property
    def direccion(self) -> str | None:
        return self._direccion

    def cambiar_estado(self, hacia: EstadoParticipante) -> None:
        if hacia not in _TRANSICIONES.get(self._estado, frozenset()):
            raise TransicionInvalida(
                "Transición de estado de participante no permitida.",
                {"desde": self._estado.value, "hacia": hacia.value},
            )
        self._estado = hacia

    def editar_contacto(self, telefono: str | None, direccion: str | None) -> None:
        self._telefono = telefono
        self._direccion = direccion
