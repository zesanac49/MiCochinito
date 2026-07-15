"""Periodicidad: división de la cuota y generación de sub-períodos (RF-301)."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.contabilidad.domain.periodos import calcular_periodos
from app.modules.natilleras.domain.configuracion import Periodicidad
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorMonetario


def test_cobros_por_mes() -> None:
    assert Periodicidad.MENSUAL.cobros_por_mes() == 1
    assert Periodicidad.QUINCENAL.cobros_por_mes() == 2
    assert Periodicidad.SEMANAL.cobros_por_mes() == 4


def test_dividir_entre() -> None:
    assert Dinero("90000").dividir_entre(2) == Dinero("45000.00")
    assert Dinero("50000").dividir_entre(1) == Dinero("50000.00")
    with pytest.raises(ErrorMonetario):
        Dinero("100").dividir_entre(0)


def test_calcular_periodos_mensual() -> None:
    p = calcular_periodos(date(2026, 1, 1), date(2026, 3, 31), 5, cobros_por_mes=1)
    # 3 meses × 1 = 3 períodos, todos secuencia 1.
    assert [(a, m, s) for a, m, s, _ in p] == [(2026, 1, 1), (2026, 2, 1), (2026, 3, 1)]


def test_calcular_periodos_quincenal() -> None:
    p = calcular_periodos(date(2026, 1, 1), date(2026, 2, 28), 5, cobros_por_mes=2)
    # 2 meses × 2 = 4 sub-períodos con secuencia 1 y 2.
    assert [(a, m, s) for a, m, s, _ in p] == [
        (2026, 1, 1),
        (2026, 1, 2),
        (2026, 2, 1),
        (2026, 2, 2),
    ]
    # La 2ª quincena de enero cae el último día del mes.
    enero_2 = next(f for a, m, s, f in p if a == 2026 and m == 1 and s == 2)
    assert enero_2 == date(2026, 1, 31)
