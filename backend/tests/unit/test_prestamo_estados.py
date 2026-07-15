"""Máquina de estados del préstamo (RN-032)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.prestamos.domain.estados import EstadoPrestamo as E
from app.modules.prestamos.domain.prestamo import Prestamo
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import TransicionInvalida
from app.shared.domain.tasa import TasaInteres


def _nuevo() -> Prestamo:
    return Prestamo.solicitar(1, Dinero("1000000"), TasaInteres(Decimal("2")), 12)


def test_rechazo_antes_de_desembolso() -> None:
    p = _nuevo()
    p.rechazar("sin capacidad de pago")
    assert p.estado is E.RECHAZADO
    assert p.motivo_rechazo == "sin capacidad de pago"


def test_no_se_puede_desembolsar_sin_aprobar() -> None:
    with pytest.raises(TransicionInvalida):
        _nuevo().desembolsar(date(2026, 1, 1))


def test_mora_y_regularizacion() -> None:
    p = _nuevo()
    p.aprobar()
    p.desembolsar(date(2026, 1, 1))
    p.marcar_mora()
    assert p.estado is E.EN_MORA
    p.regularizar()
    assert p.estado is E.EN_PAGO


def test_no_se_paga_un_prestamo_solicitado() -> None:
    with pytest.raises(TransicionInvalida):
        _nuevo().registrar_pago(Dinero("1000"), date(2026, 1, 1))
