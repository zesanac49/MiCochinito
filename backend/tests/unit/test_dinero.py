"""Tests del value object `Dinero` (TEC-01/04, doc 05 §9 — propiedad).

`Dinero` es el guardián monetario: si falla, todo el sistema financiero falla.
Cubrimos con ejemplos las reglas duras y con hypothesis las propiedades
algebraicas que deben cumplirse para cualquier monto.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorMonetario

# Estrategia: montos como Decimal de 2 decimales dentro de un rango realista.
montos = st.decimals(
    min_value=Decimal("-99999999.99"),
    max_value=Decimal("99999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


# --- Construcción y reglas duras -------------------------------------------


def test_prohibe_construccion_desde_float() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(1000.50)  # type: ignore[arg-type]


def test_prohibe_bool() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(True)  # type: ignore[arg-type]


def test_acepta_str_int_decimal() -> None:
    assert Dinero("1000.00").monto == Decimal("1000.00")
    assert Dinero(1000).monto == Decimal("1000.00")
    assert Dinero(Decimal("1000")).monto == Decimal("1000.00")


def test_moneda_es_cop() -> None:
    assert Dinero("1").moneda == "COP"


def test_redondeo_half_up_a_dos_decimales() -> None:
    assert Dinero("1.005").monto == Decimal("1.01")
    assert Dinero("1.004").monto == Decimal("1.00")


def test_rechaza_valor_no_numerico() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("no-es-numero")


def test_como_str_siempre_dos_decimales() -> None:
    assert Dinero("1000").como_str() == "1000.00"
    assert Dinero(Decimal("1250000.5")).como_str() == "1250000.50"


# --- Inmutabilidad ----------------------------------------------------------


def test_es_inmutable() -> None:
    d = Dinero("100")
    with pytest.raises(ErrorMonetario):
        d._monto = Decimal("200")  # type: ignore[misc]


# --- Aritmética entre Dinero -----------------------------------------------


def test_suma_y_resta_entre_dinero() -> None:
    assert Dinero("100.00") + Dinero("50.50") == Dinero("150.50")
    assert Dinero("100.00") - Dinero("50.50") == Dinero("49.50")


def test_no_opera_con_int() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("100") + 100  # type: ignore[operator]


def test_multiplicacion_por_entero() -> None:
    assert Dinero("1000.00").multiplicado_por(3) == Dinero("3000.00")
    assert Dinero("1000.00") * 3 == Dinero("3000.00")
    assert 3 * Dinero("1000.00") == Dinero("3000.00")


def test_multiplicacion_prohibe_float() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("1000.00") * 1.5  # type: ignore[operator]


def test_comparaciones_solo_entre_dinero() -> None:
    assert Dinero("100") < Dinero("200")
    assert Dinero("200") >= Dinero("200")
    with pytest.raises(ErrorMonetario):
        _ = Dinero("100") < 200  # type: ignore[operator]


def test_predicados_de_signo() -> None:
    assert Dinero("0").es_cero()
    assert Dinero("1").es_positivo()
    assert Dinero("-1").es_negativo()


# --- Propiedades (hypothesis) ----------------------------------------------


@given(montos)
def test_prop_ida_y_vuelta_str(m: Decimal) -> None:
    d = Dinero(m)
    assert Dinero(d.como_str()) == d


@given(montos, montos)
def test_prop_suma_conmutativa(a: Decimal, b: Decimal) -> None:
    assert Dinero(a) + Dinero(b) == Dinero(b) + Dinero(a)


@given(montos, montos, montos)
def test_prop_suma_asociativa(a: Decimal, b: Decimal, c: Decimal) -> None:
    izquierda = (Dinero(a) + Dinero(b)) + Dinero(c)
    derecha = Dinero(a) + (Dinero(b) + Dinero(c))
    assert izquierda == derecha


@given(montos, montos)
def test_prop_suma_resta_inversa(a: Decimal, b: Decimal) -> None:
    assert (Dinero(a) + Dinero(b)) - Dinero(b) == Dinero(a)


@given(montos)
def test_prop_siempre_dos_decimales(m: Decimal) -> None:
    d = Dinero(m)
    exponente = d.monto.as_tuple().exponent
    assert exponente == -2


@given(montos, st.integers(min_value=0, max_value=1000))
def test_prop_multiplicacion_equivale_a_suma_repetida(m: Decimal, n: int) -> None:
    producto = Dinero(m).multiplicado_por(n)
    acumulado = Dinero.cero()
    for _ in range(n):
        acumulado = acumulado + Dinero(m)
    assert producto == acumulado
