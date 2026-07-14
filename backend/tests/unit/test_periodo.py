"""Tests del value object `Periodo`."""

from __future__ import annotations

import pytest

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.periodo import Periodo


def test_construccion_valida() -> None:
    p = Periodo(2026, 7)
    assert p.anio == 2026
    assert p.mes == 7
    assert str(p) == "2026-07"


@pytest.mark.parametrize("mes", [0, 13, -1])
def test_mes_invalido(mes: int) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Periodo(2026, mes)


def test_anio_fuera_de_rango() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Periodo(1999, 1)


def test_siguiente_avanza_mes_y_anio() -> None:
    assert Periodo(2026, 7).siguiente() == Periodo(2026, 8)
    assert Periodo(2026, 12).siguiente() == Periodo(2027, 1)


def test_orden() -> None:
    assert Periodo(2026, 1) < Periodo(2026, 2)
    assert Periodo(2026, 12) < Periodo(2027, 1)
    assert Periodo(2026, 5) == Periodo(2026, 5)


def test_es_inmutable() -> None:
    p = Periodo(2026, 7)
    with pytest.raises(ErrorDeValidacionDeDominio):
        p._anio = 2027  # type: ignore[misc]
