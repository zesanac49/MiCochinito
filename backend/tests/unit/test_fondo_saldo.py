"""Tests del saldo derivado del fondo (RN-063, INV-12)."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.fondo import Fondo
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen

_REF = ReferenciaOrigen(TipoOrigen.CUOTA, 1)


def _mov(naturaleza: Naturaleza, monto: str) -> Asiento:
    return Asiento(
        monto=Dinero(monto),
        naturaleza=naturaleza,
        concepto=ConceptoContable.CUOTA_AHORRO,
        fondo=TipoFondo.AHORRO,
        referencia=_REF,
        descripcion="mov",
    )


def test_saldo_credito_menos_debito() -> None:
    asientos = [
        _mov(Naturaleza.CREDITO, "1000.00"),
        _mov(Naturaleza.CREDITO, "500.00"),
        _mov(Naturaleza.DEBITO, "300.00"),
    ]
    assert Fondo.saldo(asientos) == Dinero("1200.00")


def test_saldo_vacio_es_cero() -> None:
    assert Fondo.saldo([]) == Dinero.cero()


montos = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@given(st.lists(st.tuples(st.booleans(), montos), max_size=50))
def test_prop_saldo_reconciliable(movs: list[tuple[bool, Decimal]]) -> None:
    """El saldo derivado equivale a Σ créditos − Σ débitos, exacto en Decimal."""
    asientos = [
        _mov(Naturaleza.CREDITO if es_credito else Naturaleza.DEBITO, str(m))
        for es_credito, m in movs
    ]
    esperado = Dinero.cero()
    for es_credito, m in movs:
        d = Dinero(str(m))
        esperado = esperado + d if es_credito else esperado - d
    assert Fondo.saldo(asientos) == esperado


@given(montos, st.booleans())
def test_prop_reversion_cancela_el_asiento(monto: Decimal, es_credito: bool) -> None:
    """Un asiento y su reversión (naturaleza opuesta) suman cero (RN-061)."""
    original = _mov(Naturaleza.CREDITO if es_credito else Naturaleza.DEBITO, str(monto))
    reverso = _mov(Naturaleza.DEBITO if es_credito else Naturaleza.CREDITO, str(monto))
    assert Fondo.saldo([original, reverso]) == Dinero.cero()
