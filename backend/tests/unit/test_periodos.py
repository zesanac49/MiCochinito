"""Tests del cálculo de períodos del ciclo (S2-T02)."""

from __future__ import annotations

from datetime import date

from app.modules.contabilidad.domain.periodos import calcular_periodos_mensuales


def test_ciclo_anual_genera_doce_periodos() -> None:
    periodos = calcular_periodos_mensuales(date(2026, 1, 1), date(2026, 12, 31), 5)
    assert len(periodos) == 12
    assert periodos[0] == (2026, 1, date(2026, 1, 5))
    assert periodos[-1] == (2026, 12, date(2026, 12, 5))


def test_ciclo_que_cruza_anio() -> None:
    periodos = calcular_periodos_mensuales(date(2025, 12, 1), date(2026, 2, 28), 10)
    assert [(a, m) for a, m, _ in periodos] == [(2025, 12), (2026, 1), (2026, 2)]


def test_dia_limite_se_acota_al_ultimo_dia_del_mes() -> None:
    # Febrero 2026 tiene 28 días; dia_limite 31 se acota a 28.
    periodos = calcular_periodos_mensuales(date(2026, 2, 1), date(2026, 2, 28), 31)
    assert periodos[0] == (2026, 2, date(2026, 2, 28))
