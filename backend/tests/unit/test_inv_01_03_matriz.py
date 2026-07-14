"""Tests exhaustivos de la separación de fondos (INV-01..03, doc 02 §5, S1-T04).

Se enumeran TODAS las combinaciones concepto × fondo × naturaleza y se verifica
que solo las de la matriz son aceptadas por `Fondo.validar_asiento`. El conjunto
válido está escrito a mano (no derivado de la implementación) para que el test
sea una verificación real del invariante y no una tautología.
"""

from __future__ import annotations

import itertools

import pytest

from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable as C,
)
from app.modules.contabilidad.domain.conceptos import (
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import ViolacionSeparacionDeFondos
from app.modules.contabilidad.domain.fondo import Fondo
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen

D = Naturaleza.DEBITO
Cr = Naturaleza.CREDITO
AHORRO = TipoFondo.AHORRO
RENT = TipoFondo.RENTABILIDAD

# Conjunto válido según doc 02 §5 (excluye REVERSION, que es especial).
VALIDOS: set[tuple[C, TipoFondo, Naturaleza]] = {
    (C.CUOTA_AHORRO, AHORRO, Cr),
    (C.APORTE_EXTRAORDINARIO, AHORRO, Cr),
    (C.DESEMBOLSO_PRESTAMO, AHORRO, D),
    (C.RETORNO_CAPITAL, AHORRO, Cr),
    (C.INTERES_PAGADO, RENT, Cr),
    (C.UTILIDAD_ACTIVIDAD, RENT, Cr),
    (C.PERDIDA_ACTIVIDAD, RENT, D),
    (C.MULTA_PAGADA, RENT, Cr),
    (C.DEVOLUCION_AHORRO, AHORRO, D),
    (C.DISTRIBUCION_RENTABILIDAD, RENT, D),
}

_REF = ReferenciaOrigen(TipoOrigen.CUOTA, 1)


def _asiento(concepto: C, fondo: TipoFondo, naturaleza: Naturaleza, **kw: object) -> Asiento:
    return Asiento(
        monto=Dinero("1000"),
        naturaleza=naturaleza,
        concepto=concepto,
        fondo=fondo,
        referencia=_REF,
        descripcion="prueba",
        **kw,  # type: ignore[arg-type]
    )


_NO_REVERSION = [c for c in C if c is not C.REVERSION]


@pytest.mark.parametrize(
    ("concepto", "fondo", "naturaleza"),
    list(itertools.product(_NO_REVERSION, [AHORRO, RENT], [D, Cr])),
)
def test_inv_01_03_matriz_exhaustiva(
    concepto: C, fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    fondo_obj = Fondo(fondo, natillera_id=1)
    asiento = _asiento(concepto, fondo, naturaleza)
    if (concepto, fondo, naturaleza) in VALIDOS:
        fondo_obj.validar_asiento(asiento)  # no debe lanzar
    else:
        with pytest.raises(ViolacionSeparacionDeFondos):
            fondo_obj.validar_asiento(asiento)


@pytest.mark.parametrize("fondo", [AHORRO, RENT])
@pytest.mark.parametrize("naturaleza", [D, Cr])
def test_inv_11_reversion_valida_con_referencia(
    fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    # REVERSION es espejo: válida sobre cualquier fondo/naturaleza SI referencia
    # el asiento revertido (RN-061).
    fondo_obj = Fondo(fondo, natillera_id=1)
    asiento = _asiento(C.REVERSION, fondo, naturaleza, reversa_de_id=99)
    fondo_obj.validar_asiento(asiento)


@pytest.mark.parametrize("fondo", [AHORRO, RENT])
@pytest.mark.parametrize("naturaleza", [D, Cr])
def test_reversion_sin_referencia_es_rechazada(
    fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    fondo_obj = Fondo(fondo, natillera_id=1)
    asiento = _asiento(C.REVERSION, fondo, naturaleza)  # sin reversa_de_id
    with pytest.raises(ViolacionSeparacionDeFondos):
        fondo_obj.validar_asiento(asiento)


def test_inv_01_asiento_a_fondo_equivocado_es_rechazado() -> None:
    # Asiento válido para AHORRO, pero validado por el fondo de RENTABILIDAD.
    fondo_rent = Fondo(RENT, natillera_id=1)
    asiento = _asiento(C.CUOTA_AHORRO, AHORRO, Cr)
    with pytest.raises(ViolacionSeparacionDeFondos):
        fondo_rent.validar_asiento(asiento)
