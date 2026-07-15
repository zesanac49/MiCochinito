"""Agregado `Prestamo` (doc 02 §4.4, RN-030..038).

El capital sale del Fondo de Ahorro y regresa íntegro al Fondo de Ahorro; solo
el interés va a Rentabilidad (INV-04). La descomposición de cada pago usa interés
simple sobre el saldo, interés primero:
    interes_del_periodo = saldo_capital × tasa_mensual
    el pago cubre primero el interés (→ Rentabilidad) y el resto abona capital.
"""

from __future__ import annotations

import calendar
from datetime import date

from app.modules.prestamos.domain.descomposicion import Descomposicion
from app.modules.prestamos.domain.estados import EstadoPrestamo, transicion_valida
from app.modules.prestamos.domain.excepciones import PagoInvalido
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida
from app.shared.domain.tasa import TasaInteres


def _sumar_meses(d: date, meses: int) -> date:
    """Suma `meses` a una fecha, acotando el día al último del mes destino."""
    total = d.month - 1 + meses
    anio = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def _meses_completos(desde: date, hasta: date) -> int:
    """Meses calendario completos entre dos fechas (0 si `hasta` <= `desde`)."""
    if hasta <= desde:
        return 0
    meses = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day < desde.day:
        meses -= 1
    return max(meses, 0)


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
        interes_acumulado: Dinero | None = None,
        fecha_ultimo_calculo: date | None = None,
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
        # Interés devengado no pagado y fecha hasta la que ya se calculó (interés
        # simple por meses transcurridos; el primer mes se cobra al desembolsar).
        self._interes_acumulado = interes_acumulado or Dinero.cero()
        self._fecha_ultimo_calculo = fecha_ultimo_calculo
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
    def interes_acumulado(self) -> Dinero:
        return self._interes_acumulado

    @property
    def fecha_ultimo_calculo(self) -> date | None:
        return self._fecha_ultimo_calculo

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
        préstamo queda EN_PAGO (RF-403). Se cobra el primer mes de interés desde
        el desembolso; el reloj de interés avanza un mes."""
        self._transicionar(EstadoPrestamo.DESEMBOLSADO)
        self._saldo_capital = self._capital
        self._fecha_desembolso = fecha
        self._interes_acumulado = self._capital.multiplicado_por(self._tasa.fraccion)
        self._fecha_ultimo_calculo = _sumar_meses(fecha, 1)
        self._transicionar(EstadoPrestamo.EN_PAGO)

    def marcar_mora(self) -> None:
        self._transicionar(EstadoPrestamo.EN_MORA)

    def regularizar(self) -> None:
        self._transicionar(EstadoPrestamo.EN_PAGO)

    def _devengar(self, hasta: date) -> None:
        """Acumula el interés simple de los meses completos transcurridos desde el
        último cálculo, sobre el saldo de capital vigente."""
        if self._fecha_ultimo_calculo is None or self._saldo_capital.es_cero():
            return
        meses = _meses_completos(self._fecha_ultimo_calculo, hasta)
        if meses <= 0:
            return
        interes = self._saldo_capital.multiplicado_por(self._tasa.fraccion).multiplicado_por(meses)
        self._interes_acumulado = self._interes_acumulado + interes
        self._fecha_ultimo_calculo = _sumar_meses(self._fecha_ultimo_calculo, meses)

    def interes_pendiente(self, hasta: date) -> Dinero:
        """Interés devengado no pagado a la fecha (sin mutar): el acumulado más el
        interés de los meses transcurridos desde el último cálculo (RN-072/INV-14)."""
        pendiente = self._interes_acumulado
        if self._fecha_ultimo_calculo is not None and self._saldo_capital.es_positivo():
            meses = _meses_completos(self._fecha_ultimo_calculo, hasta)
            if meses > 0:
                pendiente = pendiente + self._saldo_capital.multiplicado_por(
                    self._tasa.fraccion
                ).multiplicado_por(meses)
        return pendiente

    def registrar_pago(self, monto: Dinero, fecha: date) -> Descomposicion:
        """Devenga el interés hasta `fecha`, luego descompone el pago en interés
        (primero) y capital, reduce el saldo y marca PAGADO al saldar todo
        (RN-033..035, INV-04)."""
        if self._estado not in (EstadoPrestamo.EN_PAGO, EstadoPrestamo.EN_MORA):
            raise TransicionInvalida(
                "Solo se puede pagar un préstamo en pago o en mora.",
                {"estado": self._estado.value},
            )
        if not monto.es_positivo():
            raise PagoInvalido("El pago debe ser positivo.")

        self._devengar(fecha)
        adeudado = self._saldo_capital + self._interes_acumulado
        if monto > adeudado:
            raise PagoInvalido(
                "El pago excede lo adeudado.",
                {"monto": monto.como_str(), "adeudado": adeudado.como_str()},
            )

        interes_pagado = monto if monto <= self._interes_acumulado else self._interes_acumulado
        self._interes_acumulado = self._interes_acumulado - interes_pagado
        capital_pagado = monto - interes_pagado
        self._saldo_capital = self._saldo_capital - capital_pagado

        if self._saldo_capital.es_cero() and self._interes_acumulado.es_cero():
            self._transicionar(EstadoPrestamo.PAGADO)
        return Descomposicion(capital=capital_pagado, interes=interes_pagado)
