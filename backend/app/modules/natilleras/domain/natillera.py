"""Agregado raíz `Natillera` — tenant y máquina de estados (INV-15, RN-080/081).

Nace en BORRADOR. Solo avanza por transiciones válidas. `puede(operacion)`
expone la matriz RN-081 a todos los módulos. La creación de sus dos fondos
(RN-001) la orquesta el caso de uso `CrearNatillera` (límite de módulos: el
dominio de natilleras no conoce el dominio de contabilidad).
"""

from __future__ import annotations

from datetime import date

from app.modules.natilleras.domain.configuracion import Configuracion
from app.modules.natilleras.domain.estados import (
    EstadoNatillera,
    Operacion,
    operacion_permitida,
    transicion_valida,
)
from app.modules.natilleras.domain.eventos import NatilleraTransicionada
from app.modules.natilleras.domain.excepciones import OperacionNoPermitidaEnEstado
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida


class Natillera(RaizDeAgregado):
    def __init__(
        self,
        nombre: str,
        ciclo_inicio: date,
        ciclo_fin: date,
        estado: EstadoNatillera,
        configuracion: Configuracion | None = None,
        estrategia_congelada: bool = False,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        if not nombre.strip():
            raise ErrorDeValidacionDeDominio("La natillera requiere nombre.")
        if ciclo_fin <= ciclo_inicio:
            raise ErrorDeValidacionDeDominio(
                "El fin del ciclo debe ser posterior al inicio."
            )
        self._nombre = nombre
        self._ciclo_inicio = ciclo_inicio
        self._ciclo_fin = ciclo_fin
        self._estado = estado
        self._configuracion = configuracion
        self._estrategia_congelada = estrategia_congelada
        self.uuid = uuid

    # --- Fábrica ------------------------------------------------------------
    @classmethod
    def crear(cls, nombre: str, ciclo_inicio: date, ciclo_fin: date) -> Natillera:
        """Crea una natillera en BORRADOR (RF-101). Los dos fondos los crea el
        caso de uso que orquesta contabilidad (RN-001)."""
        return cls(nombre, ciclo_inicio, ciclo_fin, EstadoNatillera.BORRADOR)

    # --- Estado -------------------------------------------------------------
    @property
    def estado(self) -> EstadoNatillera:
        return self._estado

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def ciclo_inicio(self) -> date:
        return self._ciclo_inicio

    @property
    def ciclo_fin(self) -> date:
        return self._ciclo_fin

    @property
    def configuracion(self) -> Configuracion | None:
        return self._configuracion

    @property
    def estrategia_congelada(self) -> bool:
        return self._estrategia_congelada

    def puede(self, operacion: Operacion) -> bool:
        return operacion_permitida(self._estado, operacion)

    def exigir_puede(self, operacion: Operacion) -> None:
        if not self.puede(operacion):
            raise OperacionNoPermitidaEnEstado(
                "Operación no permitida en el estado actual.",
                {"estado": self._estado.value, "operacion": operacion.value},
            )

    def transicionar(self, hacia: EstadoNatillera) -> None:
        if not transicion_valida(self._estado, hacia):
            raise TransicionInvalida(
                "Transición de estado no permitida (RN-080).",
                {"desde": self._estado.value, "hacia": hacia.value},
            )
        self._validar_requisitos_de_entrada(hacia)
        desde = self._estado
        self._estado = hacia
        if hacia is EstadoNatillera.PENDIENTE_LIQUIDACION:
            self._estrategia_congelada = True  # se congela la estrategia (RN-073)
        if self.id is not None:
            self.registrar_evento(
                NatilleraTransicionada(natillera_id=self.id, desde=desde, hacia=hacia)
            )

    def _validar_requisitos_de_entrada(self, hacia: EstadoNatillera) -> None:
        if hacia is EstadoNatillera.ABIERTA and self._configuracion is None:
            raise TransicionInvalida(
                "No se puede abrir una natillera sin configuración (RF-103).",
                {"desde": self._estado.value, "hacia": hacia.value},
            )

    # --- Configuración ------------------------------------------------------
    def configurar(self, configuracion: Configuracion) -> None:
        """Aplica configuración (RF-102). Prohibida una vez iniciada la
        liquidación (la matriz RN-081 no permite CONFIGURAR desde
        PENDIENTE_LIQUIDACION, lo que congela la estrategia, RN-073)."""
        self.exigir_puede(Operacion.CONFIGURAR)
        self._configuracion = configuracion
