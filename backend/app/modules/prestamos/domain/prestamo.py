"""Agregado `Prestamo` (doc 02 §4.4, RN-030..038).

El capital sale del Fondo de Ahorro y regresa íntegro al Fondo de Ahorro; solo
el interés va a Rentabilidad (INV-04). La descomposición de cada pago usa interés
simple sobre el saldo, interés primero:
    interes_del_periodo = saldo_capital × tasa_mensual
    el pago cubre primero el interés (→ Rentabilidad) y el resto abona capital.
"""

from __future__ import annotations

from datetime import date

from app.modules.prestamos.domain.descomposicion import Descomposicion
from app.modules.prestamos.domain.estados import EstadoPrestamo, transicion_valida
from app.modules.prestamos.domain.excepciones import PagoInvalido
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida
from app.shared.domain.tasa import TasaInteres


class Prestamo(RaizDeAgregado):
    def __init__(
        self,
        participante_id: int,
        capital: Dinero,
        tasa: TasaInteres,
        plazo_meses: int,
        estado: EstadoPrestamo = EstadoPrestamo.SOLICITADO,
        saldo_capital: Dinero | None = None,
        fecha_desembolso: date | None = None,
        motivo_rechazo: str | None = None,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        if not capital.es_positivo():
            raise ErrorDeValidacionDeDominio("El capital debe ser positivo.")
        if plazo_meses <= 0:
            raise ErrorDeValidacionDeDominio("El plazo debe ser positivo.")
        self._participante_id = participante_id
        self._capital = capital
        self._tasa = tasa
        self._plazo_meses = plazo_meses
        self._estado = estado
        self._saldo_capital = saldo_capital if saldo_capital is not None else Dinero.cero()
        self._fecha_desembolso = fecha_desembolso
        self._motivo_rechazo = motivo_rechazo
        self.uuid = uuid

    # --- Fábrica ------------------------------------------------------------
    @classmethod
    def solicitar(
        cls, participante_id: int, capital: Dinero, tasa: TasaInteres, plazo_meses: int
    ) -> Prestamo:
        return cls(participante_id, capital, tasa, plazo_meses)

    # --- Acceso -------------------------------------------------------------
    @property
    def participante_id(self) -> int:
        return self._participante_id

    @property
    def capital(self) -> Dinero:
        return self._capital

    @property
    def tasa(self) -> TasaInteres:
        return self._tasa

    @property
    def plazo_meses(self) -> int:
        return self._plazo_meses

    @property
    def estado(self) -> EstadoPrestamo:
        return self._estado

    @property
    def saldo_capital(self) -> Dinero:
        return self._saldo_capital

    @property
    def fecha_desembolso(self) -> date | None:
        return self._fecha_desembolso

    @property
    def motivo_rechazo(self) -> str | None:
        return self._motivo_rechazo

    # --- Transiciones -------------------------------------------------------
    def _transicionar(self, hacia: EstadoPrestamo) -> None:
        if not transicion_valida(self._estado, hacia):
            raise TransicionInvalida(
                "Transición de estado de préstamo no permitida.",
                {"desde": self._estado.value, "hacia": hacia.value},
            )
        self._estado = hacia

    def aprobar(self) -> None:
        self._transicionar(EstadoPrestamo.APROBADO)

    def rechazar(self, motivo: str) -> None:
        self._transicionar(EstadoPrestamo.RECHAZADO)
        self._motivo_rechazo = motivo

    def desembolsar(self, fecha: date) -> None:
        """Desembolsa: el saldo de capital pasa a ser el capital prestado y el
        préstamo queda EN_PAGO (RF-403)."""
        self._transicionar(EstadoPrestamo.DESEMBOLSADO)
        self._saldo_capital = self._capital
        self._fecha_desembolso = fecha
        self._transicionar(EstadoPrestamo.EN_PAGO)

    def marcar_mora(self) -> None:
        self._transicionar(EstadoPrestamo.EN_MORA)

    def regularizar(self) -> None:
        self._transicionar(EstadoPrestamo.EN_PAGO)

    def registrar_pago(self, monto: Dinero) -> Descomposicion:
        """Descompone el pago en interés (primero) y capital, reduce el saldo y,
        si queda en cero, marca PAGADO (RN-033..035, INV-04)."""
        if self._estado not in (EstadoPrestamo.EN_PAGO, EstadoPrestamo.EN_MORA):
            raise TransicionInvalida(
                "Solo se puede pagar un préstamo en pago o en mora.",
                {"estado": self._estado.value},
            )
        if not monto.es_positivo():
            raise PagoInvalido("El pago debe ser positivo.")

        interes_periodo = self._saldo_capital.multiplicado_por(self._tasa.fraccion)
        adeudado = self._saldo_capital + interes_periodo
        if monto > adeudado:
            raise PagoInvalido(
                "El pago excede lo adeudado.",
                {"monto": monto.como_str(), "adeudado": adeudado.como_str()},
            )

        if monto <= interes_periodo:
            desc = Descomposicion(capital=Dinero.cero(), interes=monto)
        else:
            desc = Descomposicion(capital=monto - interes_periodo, interes=interes_periodo)

        self._saldo_capital = self._saldo_capital - desc.capital
        if self._saldo_capital.es_cero():
            self._transicionar(EstadoPrestamo.PAGADO)
        return desc
