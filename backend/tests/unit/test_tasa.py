"""Tests del VO TasaInteres (TEC-04)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.tasa import TasaInteres


def test_tasa_valida_y_fraccion() -> None:
    t = TasaInteres(Decimal("2.5"))
    assert t.porcentaje == Decimal("2.5")
    assert t.fraccion == Decimal("0.025")


def test_tasa_no_positiva() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(Decimal("0"))


def test_tasa_prohibe_float() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(2.5)  # type: ignore[arg-type]


def test_tasa_excede_tope() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(Decimal("6"), tope=Decimal("5"))


def test_tasa_dentro_del_tope() -> None:
    assert TasaInteres(Decimal("3"), tope=Decimal("5")).porcentaje == Decimal("3")
