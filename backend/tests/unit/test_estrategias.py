"""Tests de las estrategias de distribución (RN-073). Property: suma == fondo."""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.liquidacion.domain.estrategias import (
    ParticipanteLiquidable,
    crear_estrategia,
)
from app.shared.domain.dinero import Dinero


def _liq(pid: int, ahorro: str, meses: int = 12) -> ParticipanteLiquidable:
    return ParticipanteLiquidable(pid, Dinero(ahorro), meses)


def test_partes_iguales() -> None:
    est = crear_estrategia("PARTES_IGUALES")
    partes = est.distribuir(Dinero("90000"), [_liq(1, "0"), _liq(2, "0"), _liq(3, "0")])
    assert partes == {1: Dinero("30000.00"), 2: Dinero("30000.00"), 3: Dinero("30000.00")}


def test_proporcional_al_ahorro() -> None:
    est = crear_estrategia("PROPORCIONAL_AHORRO")
    # Ahorros 100k y 300k → 25% y 75% de 40.000 = 10.000 y 30.000.
    partes = est.distribuir(Dinero("40000"), [_liq(1, "100000"), _liq(2, "300000")])
    assert partes[1] == Dinero("10000.00")
    assert partes[2] == Dinero("30000.00")


def test_residuo_al_de_mayor_participacion() -> None:
    est = crear_estrategia("PARTES_IGUALES")
    # 100 / 3 = 33.33 c/u, suma 99.99, residuo 0.01 al mayor.
    partes = est.distribuir(Dinero("100.00"), [_liq(1, "0"), _liq(2, "0"), _liq(3, "0")])
    assert sum((p.monto for p in partes.values()), Decimal(0)) == Decimal("100.00")


montos = st.decimals(
    min_value=Decimal("0.00"), max_value=Decimal("99999999.99"), places=2,
    allow_nan=False, allow_infinity=False,
)
ahorros = st.decimals(
    min_value=Decimal("0.00"), max_value=Decimal("9999999.99"), places=2,
    allow_nan=False, allow_infinity=False,
)


@pytest.mark.parametrize(
    "estrategia", ["PARTES_IGUALES", "PROPORCIONAL_AHORRO", "PROPORCIONAL_TIEMPO"]
)
@settings(max_examples=50, deadline=None)
@given(
    montos,
    st.lists(st.tuples(ahorros, st.integers(min_value=1, max_value=60)), min_size=1, max_size=15),
)
def test_prop_suma_igual_al_fondo(
    estrategia: str, fondo: Decimal, datos: list[tuple[Decimal, int]]
) -> None:
    est = crear_estrategia(estrategia)
    participantes = [
        ParticipanteLiquidable(i, Dinero(a), m) for i, (a, m) in enumerate(datos, start=1)
    ]
    partes = est.distribuir(Dinero(fondo), participantes)
    total = sum((p.monto for p in partes.values()), Decimal(0))
    assert total == fondo  # cuadre exacto (RN-073)
    assert all(not p.es_negativo() for p in partes.values())
