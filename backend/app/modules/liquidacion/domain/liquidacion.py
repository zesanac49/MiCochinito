"""Agregado `Liquidacion` (doc 02 §4.7, RN-070..074).

Proceso por fases, irreversible desde CONFIRMADA (RN-074). El cálculo por
participante usa la fórmula RN-072; la distribución de rentabilidad la calcula
una `EstrategiaDistribucion` (el servicio de aplicación arma los insumos).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.modules.liquidacion.domain.excepciones import ConfirmacionIncorrecta
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import TransicionInvalida


class FaseLiquidacion(str, Enum):
    PRE_VALIDACION = "PRE_VALIDACION"
    CALCULADA = "CALCULADA"
    EN_REVISION = "EN_REVISION"
    CONFIRMADA = "CONFIRMADA"
    ACTA_GENERADA = "ACTA_GENERADA"


@dataclass(frozen=True, slots=True)
class Bloqueo:
    tipo: str
    origen_tipo: str
    origen_id: int
    descripcion: str

    def clave(self) -> tuple[str, str, int]:
        return (self.tipo, self.origen_tipo, self.origen_id)


@dataclass(frozen=True, slots=True)
class DetalleLiquidacion:
    participante_id: int
    ahorros: Dinero
    participacion_rentabilidad: Dinero
    capital_pendiente: Dinero
    intereses_pendientes: Dinero
    multas_pendientes: Dinero

    @property
    def saldo_final(self) -> Dinero:
        return (
            self.ahorros
            + self.participacion_rentabilidad
            - self.capital_pendiente
            - self.intereses_pendientes
            - self.multas_pendientes
        )


class Liquidacion(RaizDeAgregado):
    def __init__(
        self,
        natillera_id: int,
        fase: FaseLiquidacion = FaseLiquidacion.PRE_VALIDACION,
        estrategia_aplicada: str | None = None,
        saldo_rentabilidad_distribuido: Dinero | None = None,
        detalles: list[DetalleLiquidacion] | None = None,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        self._natillera_id = natillera_id
        self._fase = fase
        self._estrategia = estrategia_aplicada
        self._saldo_rentabilidad = saldo_rentabilidad_distribuido or Dinero.cero()
        self._detalles: list[DetalleLiquidacion] = list(detalles or [])
        self.uuid = uuid

    @property
    def natillera_id(self) -> int:
        return self._natillera_id

    @property
    def fase(self) -> FaseLiquidacion:
        return self._fase

    @property
    def estrategia_aplicada(self) -> str | None:
        return self._estrategia

    @property
    def saldo_rentabilidad_distribuido(self) -> Dinero:
        return self._saldo_rentabilidad

    @property
    def detalles(self) -> list[DetalleLiquidacion]:
        return list(self._detalles)

    def registrar_calculo(
        self, estrategia: str, detalles: list[DetalleLiquidacion], saldo_rentabilidad: Dinero
    ) -> None:
        if self._fase not in (FaseLiquidacion.PRE_VALIDACION, FaseLiquidacion.CALCULADA):
            raise TransicionInvalida(
                "La liquidación no puede recalcularse en este estado.",
                {"fase": self._fase.value},
            )
        self._estrategia = estrategia
        self._detalles = list(detalles)
        self._saldo_rentabilidad = saldo_rentabilidad
        self._fase = FaseLiquidacion.CALCULADA

    def confirmar(self, nombre_ingresado: str, nombre_real: str) -> None:
        if self._fase is not FaseLiquidacion.CALCULADA:
            raise TransicionInvalida(
                "Solo una liquidación calculada puede confirmarse.",
                {"fase": self._fase.value},
            )
        if nombre_ingresado.strip() != nombre_real.strip():
            raise ConfirmacionIncorrecta(
                "El nombre ingresado no coincide con el de la natillera (RF-704)."
            )
        self._fase = FaseLiquidacion.CONFIRMADA
