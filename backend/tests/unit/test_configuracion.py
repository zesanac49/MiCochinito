"""Tests de la entidad Configuracion (RF-102)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.natilleras.domain.configuracion import (
    Configuracion,
    EstrategiaDistribucion,
    Periodicidad,
)
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


def _config(**overrides: object) -> Configuracion:
    base: dict[str, object] = {
        "valor_cuota": Dinero("50000"),
        "periodicidad_cuota": Periodicidad.MENSUAL,
        "dia_limite_pago": 5,
        "permite_aportes_extra": True,
        "tasa_interes_base": Decimal("2.0"),
        "tasa_interes_min": Decimal("1.0"),
        "tasa_interes_max": Decimal("3.0"),
        "max_prestamos_activos": 2,
        "max_capital_vigente": Dinero("2000000"),
        "estrategia_distribucion": EstrategiaDistribucion.PROPORCIONAL_AHORRO,
    }
    base.update(overrides)
    return Configuracion(**base)  # type: ignore[arg-type]


def test_configuracion_valida() -> None:
    c = _config()
    assert c.valor_cuota == Dinero("50000")


def test_dia_limite_invalido() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        _config(dia_limite_pago=0)
    with pytest.raises(ErrorDeValidacionDeDominio):
        _config(dia_limite_pago=32)


def test_tasas_deben_estar_ordenadas() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        _config(tasa_interes_base=Decimal("5.0"))  # base > max


def test_tasa_no_positiva() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        _config(tasa_interes_min=Decimal("0"))


def test_max_prestamos_minimo_uno() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        _config(max_prestamos_activos=0)
