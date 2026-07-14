"""Tests de la máquina de estados de la natillera (INV-15, RN-080/081, S1-T02)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.natilleras.domain.configuracion import (
    Configuracion,
    EstrategiaDistribucion,
    Periodicidad,
)
from app.modules.natilleras.domain.estados import EstadoNatillera as E
from app.modules.natilleras.domain.estados import Operacion as Op
from app.modules.natilleras.domain.excepciones import OperacionNoPermitidaEnEstado
from app.modules.natilleras.domain.natillera import Natillera
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import TransicionInvalida


def _config() -> Configuracion:
    return Configuracion(
        valor_cuota=Dinero("50000"),
        periodicidad_cuota=Periodicidad.MENSUAL,
        dia_limite_pago=5,
        permite_aportes_extra=True,
        tasa_interes_base=Decimal("2.0"),
        tasa_interes_min=Decimal("1.0"),
        tasa_interes_max=Decimal("3.0"),
        max_prestamos_activos=2,
        max_capital_vigente=Dinero("2000000"),
        estrategia_distribucion=EstrategiaDistribucion.PROPORCIONAL_AHORRO,
    )


def _natillera(estado: E = E.BORRADOR) -> Natillera:
    n = Natillera("Los Ahorradores", date(2026, 1, 1), date(2026, 12, 31), estado)
    n._asignar_id(1)
    return n


def test_crear_nace_en_borrador() -> None:
    n = Natillera.crear("N", date(2026, 1, 1), date(2026, 12, 31))
    assert n.estado is E.BORRADOR


SECUENCIA_VALIDA = [
    (E.BORRADOR, E.ABIERTA),
    (E.ABIERTA, E.EN_OPERACION),
    (E.EN_OPERACION, E.PENDIENTE_LIQUIDACION),
    (E.PENDIENTE_LIQUIDACION, E.LIQUIDADA),
    (E.LIQUIDADA, E.ARCHIVADA),
]


@pytest.mark.parametrize(("desde", "hacia"), SECUENCIA_VALIDA)
def test_inv_15_transiciones_validas(desde: E, hacia: E) -> None:
    n = _natillera(desde)
    if hacia is E.ABIERTA:
        n.configurar(_config())  # requisito de entrada
    n.transicionar(hacia)
    assert n.estado is hacia


@pytest.mark.parametrize("hacia", [E.EN_OPERACION, E.LIQUIDADA, E.ARCHIVADA])
def test_inv_15_saltos_prohibidos_desde_borrador(hacia: E) -> None:
    with pytest.raises(TransicionInvalida):
        _natillera(E.BORRADOR).transicionar(hacia)


def test_inv_15_no_retrocede() -> None:
    with pytest.raises(TransicionInvalida):
        _natillera(E.EN_OPERACION).transicionar(E.ABIERTA)


def test_abrir_sin_configuracion_falla() -> None:
    with pytest.raises(TransicionInvalida):
        _natillera(E.BORRADOR).transicionar(E.ABIERTA)


def test_puede_operacion_por_estado() -> None:
    assert _natillera(E.EN_OPERACION).puede(Op.MOVIMIENTO_FINANCIERO)
    assert not _natillera(E.BORRADOR).puede(Op.MOVIMIENTO_FINANCIERO)
    assert _natillera(E.LIQUIDADA).puede(Op.ENTREGAR_EFECTIVO)
    assert not _natillera(E.LIQUIDADA).puede(Op.CREAR_PRESTAMO)


def test_configurar_bloqueado_en_pendiente_liquidacion() -> None:
    n = _natillera(E.PENDIENTE_LIQUIDACION)
    with pytest.raises(OperacionNoPermitidaEnEstado):
        n.configurar(_config())


def test_estrategia_se_congela_al_entrar_a_pendiente() -> None:
    n = _natillera(E.EN_OPERACION)
    assert not n.estrategia_congelada
    n.transicionar(E.PENDIENTE_LIQUIDACION)
    assert n.estrategia_congelada


def test_transicion_registra_evento() -> None:
    n = _natillera(E.EN_OPERACION)
    n.transicionar(E.PENDIENTE_LIQUIDACION)
    eventos = n.extraer_eventos()
    assert len(eventos) == 1
    assert eventos[0].hacia is E.PENDIENTE_LIQUIDACION  # type: ignore[attr-defined]
