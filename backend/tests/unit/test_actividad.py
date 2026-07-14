"""Tests del agregado Actividad (INV-05..09, RN-040..049, S4-T01..T05)."""

from __future__ import annotations

import pytest

from app.modules.actividades.domain.actividad import Actividad
from app.modules.actividades.domain.estados import (
    EstadoActividad,
    TipoActividad,
    TipoMovimiento,
)
from app.modules.actividades.domain.excepciones import (
    NumeroNoDisponible,
    SorteoYaRegistrado,
)
from app.shared.domain.dinero import Dinero


def _polla(cantidad: int = 5) -> Actividad:
    a = Actividad.crear(
        TipoActividad.POLLA,
        "Polla de enero",
        periodo_id=1,
        valor_numero=Dinero("10000"),
        cantidad_numeros=cantidad,
    )
    a.abrir()
    return a


def test_utilidad_ingresos_menos_premios_menos_gastos() -> None:
    a = _polla()
    a.asignar_numero(1, participante_id=10)
    a.asignar_numero(2, participante_id=20)
    a.marcar_pago_numero(1)  # +10.000 ingreso
    a.marcar_pago_numero(2)  # +10.000 ingreso
    a.registrar_movimiento(TipoMovimiento.GASTO, "Impresión", Dinero("5000"))
    # Sin sorteo aún: utilidad = 20.000 - 0 - 5.000 = 15.000
    assert a.utilidad() == Dinero("15000.00")


def test_inv07_solo_numeros_pagados_participan() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    a.asignar_numero(2, 20)
    a.marcar_pago_numero(1)  # solo el 1 pagó
    activos = [n.numero for n in a.numeros_activos()]
    assert activos == [1]


def test_inv07_numero_no_pagado_nunca_gana() -> None:
    a = _polla()
    a.asignar_numero(3, 30)  # asignado pero NO pagado
    sorteo = a.sortear(3, fuente="Lotería de Bogotá")
    assert sorteo.hubo_ganador is False
    assert sorteo.participante_ganador_id is None


def test_sorteo_ganador_premio_es_el_pozo() -> None:
    a = _polla()
    for numero, pid in [(1, 10), (2, 20), (3, 30)]:
        a.asignar_numero(numero, pid)
        a.marcar_pago_numero(numero)  # 3 pagados => pozo = 30.000
    sorteo = a.sortear(2, fuente="Lotería")
    assert sorteo.hubo_ganador is True
    assert sorteo.participante_ganador_id == 20
    # El premio es todo el pozo (valor_numero × pagados).
    assert a.premio_calculado() == Dinero("30000.00")
    premios = [m for m in a.movimientos if m.tipo is TipoMovimiento.PREMIO]
    assert len(premios) == 1
    assert premios[0].valor == Dinero("30000.00")
    # El ganador se lleva el pozo: el fondo no gana en esta polla (utilidad 0).
    assert a.utilidad() == Dinero("0.00")


def test_inv09_sin_ganador_no_hay_premio() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    a.marcar_pago_numero(1)  # ingreso 10.000
    a.sortear(2, fuente="Lotería")  # el 2 no está pagado -> sin ganador
    # Sin premio: utilidad = 10.000 (íntegra a Rentabilidad, INV-09)
    assert a.utilidad() == Dinero("10000.00")


def test_sorteo_es_inmutable() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    a.marcar_pago_numero(1)
    a.sortear(1, fuente="Lotería")
    with pytest.raises(SorteoYaRegistrado):
        a.sortear(1, fuente="Otra")


def test_numero_duplicado_no_disponible() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    with pytest.raises(NumeroNoDisponible):
        a.asignar_numero(1, 20)


def test_cerrar_devuelve_utilidad_y_cambia_estado() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    a.marcar_pago_numero(1)
    utilidad = a.cerrar()
    assert utilidad == Dinero("10000.00")
    assert a.estado is EstadoActividad.CERRADA


def test_inv08_clonacion_copia_numeros_excluye_pagos_y_sorteo() -> None:
    a = _polla()
    a.asignar_numero(1, 10)
    a.asignar_numero(2, 20)
    a.marcar_pago_numero(1)
    a.sortear(1, fuente="Lotería")

    clon = a.clonar_para(periodo_id=2)
    assert clon.estado is EstadoActividad.BORRADOR
    # Copia números y asignación...
    assert [(n.numero, n.participante_id) for n in clon.numeros] == [(1, 10), (2, 20)]
    # ...pero NINGUNO pagado, sin sorteo ni movimientos (INV-08/RN-049).
    assert all(not n.pagado for n in clon.numeros)
    assert clon.sorteo is None
    assert clon.movimientos == []
    assert clon.clonada_de_id == a.id
