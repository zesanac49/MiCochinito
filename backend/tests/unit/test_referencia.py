"""Tests del value object `ReferenciaOrigen`."""

from __future__ import annotations

import pytest

from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


def test_construccion_valida() -> None:
    ref = ReferenciaOrigen(TipoOrigen.PRESTAMO, 42)
    assert ref.tipo is TipoOrigen.PRESTAMO
    assert ref.id_origen == 42


def test_id_invalido() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        ReferenciaOrigen(TipoOrigen.CUOTA, 0)
    with pytest.raises(ErrorDeValidacionDeDominio):
        ReferenciaOrigen(TipoOrigen.CUOTA, -1)


def test_tipo_invalido() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        ReferenciaOrigen("PRESTAMO", 1)  # type: ignore[arg-type]


def test_igualdad_por_valor() -> None:
    a = ReferenciaOrigen(TipoOrigen.MULTA, 7)
    b = ReferenciaOrigen(TipoOrigen.MULTA, 7)
    assert a == b
    assert hash(a) == hash(b)
