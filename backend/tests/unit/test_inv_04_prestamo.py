"""Descomposición de pagos e INV-04 (capital nunca genera utilidad, S3-T03).

El capital retorna íntegro al Fondo de Ahorro: la suma de los componentes de
capital a lo largo del préstamo es exactamente el capital original. El interés se
calcula sobre el saldo (interés primero). Property tests en Decimal exacto.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.prestamos.domain.estados import EstadoPrestamo
from app.modules.prestamos.domain.excepciones import PagoInvalido
from app.modules.prestamos.domain.prestamo import Prestamo
from app.shared.domain.dinero import Dinero
from app.shared.domain.tasa import TasaInteres

_FECHA = date(2026, 1, 15)  # se desembolsa y paga el mismo día → 1 mes de interés


def _prestamo(capital: str = "1000000", tasa: str = "2") -> Prestamo:
    p = Prestamo.solicitar(1, Dinero(capital), TasaInteres(Decimal(tasa)), plazo_meses=12)
    p.aprobar()
    p.desembolsar(_FECHA)
    return p


def test_desembolso_deja_saldo_igual_al_capital() -> None:
    p = _prestamo()
    assert p.estado is EstadoPrestamo.EN_PAGO
    assert p.saldo_capital == Dinero("1000000")


def test_pago_interes_primero() -> None:
    p = _prestamo(capital="1000000", tasa="2")  # primer mes de interés = 20.000
    desc = p.registrar_pago(Dinero("120000"), _FECHA)
    assert desc.interes == Dinero("20000.00")
    assert desc.capital == Dinero("100000.00")
    assert desc.capital + desc.interes == Dinero("120000.00")
    assert p.saldo_capital == Dinero("900000.00")


def test_pago_menor_al_interes_no_abona_capital() -> None:
    p = _prestamo(capital="1000000", tasa="2")  # interés = 20.000
    desc = p.registrar_pago(Dinero("15000"), _FECHA)
    assert desc.capital.es_cero()
    assert desc.interes == Dinero("15000.00")
    assert p.saldo_capital == Dinero("1000000.00")


def test_pago_total_marca_pagado() -> None:
    p = _prestamo(capital="1000000", tasa="2")
    # Adeudado = saldo + interés = 1.020.000
    p.registrar_pago(Dinero("1020000"), _FECHA)
    assert p.estado is EstadoPrestamo.PAGADO
    assert p.saldo_capital.es_cero()


def test_interes_por_meses_transcurridos() -> None:
    # Sin pagar, a 3 meses del desembolso se deben 3 meses de interés.
    p = _prestamo(capital="1000000", tasa="3")
    assert p.interes_pendiente(date(2026, 4, 15)) == Dinero("90000.00")


def test_pago_excede_adeudado_es_rechazado() -> None:
    p = _prestamo(capital="1000000", tasa="2")
    with pytest.raises(PagoInvalido):
        p.registrar_pago(Dinero("2000000"), _FECHA)


capitales = st.decimals(
    min_value=Decimal("1000.00"), max_value=Decimal("9999999.99"), places=2,
    allow_nan=False, allow_infinity=False,
)
tasas = st.decimals(
    min_value=Decimal("0.5"), max_value=Decimal("5.0"), places=2,
    allow_nan=False, allow_infinity=False,
)


@settings(max_examples=60, deadline=None)
@given(capitales, tasas)
def test_prop_inv_04_capital_retorna_integro(capital: Decimal, tasa: Decimal) -> None:
    """Al terminar de pagar, la suma de componentes de capital == capital."""
    p = _prestamo(capital=str(capital), tasa=str(tasa))
    capital_acumulado = Dinero.cero()
    guarda = 0
    while p.estado is not EstadoPrestamo.PAGADO and guarda < 500:
        guarda += 1
        interes = p.interes_pendiente(_FECHA)  # interés real devengado a la fecha
        adeudado = p.saldo_capital + interes
        # Paga el interés + un trozo de capital (o liquida si el saldo es pequeño).
        chunk = Dinero("50000")
        monto = adeudado if p.saldo_capital <= chunk else interes + chunk
        desc = p.registrar_pago(monto, _FECHA)
        assert desc.capital + desc.interes == monto  # RN-033 exacto
        capital_acumulado = capital_acumulado + desc.capital
    assert p.estado is EstadoPrestamo.PAGADO
    assert capital_acumulado == Dinero(capital)  # INV-04
