"""Casos borde del agregado `Actividad` (INV-05..09, RN-040..049).

Complementa `test_actividad.py` con cobertura exhaustiva del dominio: premio =
pozo (Σingresos), sorteo, gestión de números, movimientos, cierre y clonación
(INV-08). Todo se ejercita contra la API real del agregado (Python puro, sin
FastAPI ni SQLAlchemy).
"""

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
from app.shared.domain.excepciones import (
    ErrorDeValidacionDeDominio,
    TransicionInvalida,
)

# --- Helpers de construcción -----------------------------------------------


def _nueva(valor: str | None = "10000", cantidad: int | None = 5) -> Actividad:
    """Actividad POLLA en BORRADOR."""
    return Actividad.crear(
        TipoActividad.POLLA,
        "Polla de enero",
        periodo_id=1,
        valor_numero=Dinero(valor) if valor is not None else None,
        cantidad_numeros=cantidad,
    )


def _abierta(valor: str | None = "10000", cantidad: int | None = 5) -> Actividad:
    a = _nueva(valor, cantidad)
    a.abrir()
    return a


def _con_pagados(
    pagados: list[int], cantidad: int = 5, valor: str = "10000"
) -> Actividad:
    """Actividad ABIERTA con todos los números asignados y `pagados` marcados."""
    a = _abierta(valor, cantidad)
    for i in range(1, cantidad + 1):
        a.asignar_numero(i, participante_id=i * 10)
    for numero in pagados:
        a.marcar_pago_numero(numero)
    return a


def _en_estado_no_editable(estado: EstadoActividad) -> Actividad:
    """Actividad en SORTEADA o CERRADA (los dos estados no editables)."""
    a = _con_pagados([1])
    if estado is EstadoActividad.SORTEADA:
        a.sortear(1, fuente="Lotería")
    elif estado is EstadoActividad.CERRADA:
        a.cerrar()
    else:  # pragma: no cover - guardia de uso
        raise AssertionError(f"Estado no soportado por el helper: {estado}")
    assert a.estado is estado
    return a


_NO_EDITABLES = [EstadoActividad.SORTEADA, EstadoActividad.CERRADA]


# ===========================================================================
# Premio = pozo (Σ ingresos)
# ===========================================================================


@pytest.mark.parametrize("cantidad", [1, 3, 5])
def test_pozo_cero_sin_numeros_pagados(cantidad: int) -> None:
    """Sin pagos no hay ingresos: el pozo es cero (aunque haya asignados)."""
    a = _abierta(cantidad=cantidad)
    for i in range(1, cantidad + 1):
        a.asignar_numero(i, participante_id=i)
    assert a.premio_calculado() == Dinero("0.00")
    assert a.premio_calculado().es_cero()


def test_pozo_cero_actividad_recien_abierta() -> None:
    assert _abierta().premio_calculado() == Dinero("0.00")


@pytest.mark.parametrize(
    ("valor", "pagados", "esperado"),
    [
        ("10000", [1], "10000.00"),
        ("10000", [1, 2], "20000.00"),
        ("10000", [1, 2, 3], "30000.00"),
        ("10000", [1, 2, 3, 4, 5], "50000.00"),
        ("7500.50", [1, 2], "15001.00"),
        ("1", [1, 2, 3, 4], "4.00"),
    ],
)
def test_pozo_es_valor_numero_por_pagados(
    valor: str, pagados: list[int], esperado: str
) -> None:
    """Pozo = valor_numero × cantidad de números pagados (RF-503 ajustado)."""
    a = _con_pagados(pagados, cantidad=5, valor=valor)
    assert a.premio_calculado() == Dinero(esperado)
    assert len(a.numeros_activos()) == len(pagados)


@pytest.mark.parametrize("repeticiones", [2, 3, 5])
def test_marcar_pago_es_idempotente_en_el_pozo(repeticiones: int) -> None:
    """Marcar el pago varias veces no infla el pozo (idempotente)."""
    a = _abierta()
    a.asignar_numero(1, participante_id=10)
    for _ in range(repeticiones):
        a.marcar_pago_numero(1)
    assert a.premio_calculado() == Dinero("10000.00")


def test_marcar_pago_idempotente_no_duplica_ingreso() -> None:
    """La segunda marca de pago no agrega otro movimiento de INGRESO."""
    a = _abierta()
    a.asignar_numero(1, participante_id=10)
    a.marcar_pago_numero(1)
    a.marcar_pago_numero(1)
    ingresos = [m for m in a.movimientos if m.tipo is TipoMovimiento.INGRESO]
    assert len(ingresos) == 1
    assert ingresos[0].valor == Dinero("10000.00")


# ===========================================================================
# Sorteo
# ===========================================================================


@pytest.mark.parametrize("ganador", [1, 2, 3])
def test_sorteo_ganador_pagado_premio_es_el_pozo(ganador: int) -> None:
    a = _con_pagados([1, 2, 3])  # pozo = 30.000
    sorteo = a.sortear(ganador, fuente="Lotería")
    assert sorteo.hubo_ganador is True
    assert sorteo.participante_ganador_id == ganador * 10
    assert a.estado is EstadoActividad.SORTEADA
    premios = [m for m in a.movimientos if m.tipo is TipoMovimiento.PREMIO]
    assert len(premios) == 1
    assert premios[0].valor == Dinero("30000.00")


@pytest.mark.parametrize(
    ("gasto", "utilidad_esperada"),
    [
        (None, "0.00"),
        ("5000", "-5000.00"),
        ("12345.67", "-12345.67"),
        ("30000", "-30000.00"),
    ],
)
def test_sorteo_con_ganador_utilidad_es_menos_gastos(
    gasto: str | None, utilidad_esperada: str
) -> None:
    """Con ganador el pozo entero es premio, así que utilidad = −gastos."""
    a = _con_pagados([1, 2, 3])  # pozo = 30.000
    if gasto is not None:
        a.registrar_movimiento(TipoMovimiento.GASTO, "Impresión", Dinero(gasto))
    a.sortear(2, fuente="Lotería")
    assert a.utilidad() == Dinero(utilidad_esperada)


@pytest.mark.parametrize("no_pagado", [4, 5])
def test_sorteo_numero_no_pagado_no_gana_utilidad_integra(no_pagado: int) -> None:
    """INV-07/09: un número asignado pero no pagado nunca gana; el pozo íntegro
    queda como utilidad."""
    a = _con_pagados([1, 2])  # pozo = 20.000; 4 y 5 asignados sin pagar
    sorteo = a.sortear(no_pagado, fuente="Lotería")
    assert sorteo.hubo_ganador is False
    assert sorteo.participante_ganador_id is None
    assert a.utilidad() == Dinero("20000.00")
    assert [m for m in a.movimientos if m.tipo is TipoMovimiento.PREMIO] == []


@pytest.mark.parametrize("numero", [2, 4])
def test_sorteo_numero_no_asignado_sin_ganador(numero: int) -> None:
    """Un número que no existe en la actividad no puede ganar (INV-09)."""
    a = _abierta()
    a.asignar_numero(1, participante_id=10)
    a.marcar_pago_numero(1)  # solo el 1 existe y está pagado
    sorteo = a.sortear(numero, fuente="Lotería")
    assert sorteo.hubo_ganador is False
    assert a.utilidad() == Dinero("10000.00")


def test_sortear_dos_veces_lanza_sorteo_ya_registrado() -> None:
    a = _con_pagados([1])
    a.sortear(1, fuente="Lotería")
    with pytest.raises(SorteoYaRegistrado):
        a.sortear(1, fuente="Otra")


def test_sortear_en_borrador_transicion_invalida() -> None:
    """Solo una actividad ABIERTA puede sortearse."""
    a = _nueva()  # BORRADOR, sin sorteo
    with pytest.raises(TransicionInvalida):
        a.sortear(1, fuente="Lotería")


def test_sortear_en_cerrada_transicion_invalida() -> None:
    a = _con_pagados([1])
    a.cerrar()  # CERRADA sin sorteo previo
    with pytest.raises(TransicionInvalida):
        a.sortear(1, fuente="Lotería")


# ===========================================================================
# Números (asignación y pago)
# ===========================================================================


@pytest.mark.parametrize("numero", [0, -1, 6, 7, 100])
def test_asignar_numero_fuera_de_rango(numero: int) -> None:
    """NumeroPolla valida el rango [1, cantidad] al asignar."""
    a = _abierta(cantidad=5)
    with pytest.raises(ErrorDeValidacionDeDominio):
        a.asignar_numero(numero, participante_id=10)


@pytest.mark.parametrize("numero", [1, 3, 5])
def test_asignar_numero_valido_ok(numero: int) -> None:
    a = _abierta(cantidad=5)
    a.asignar_numero(numero, participante_id=99)
    asignados = [n.numero for n in a.numeros]
    assert numero in asignados
    assert all(not n.pagado for n in a.numeros)


def test_asignar_numero_duplicado_no_disponible() -> None:
    a = _abierta()
    a.asignar_numero(1, participante_id=10)
    with pytest.raises(NumeroNoDisponible):
        a.asignar_numero(1, participante_id=20)


def test_asignar_sin_cantidad_configurada() -> None:
    a = _abierta(cantidad=None)
    with pytest.raises(ErrorDeValidacionDeDominio):
        a.asignar_numero(1, participante_id=10)


@pytest.mark.parametrize("numero", [2, 3, 99])
def test_pagar_numero_inexistente(numero: int) -> None:
    a = _abierta()
    a.asignar_numero(1, participante_id=10)  # solo existe el 1
    with pytest.raises(NumeroNoDisponible):
        a.marcar_pago_numero(numero)


def test_marcar_pago_sin_valor_numero() -> None:
    a = _abierta(valor=None, cantidad=5)
    a.asignar_numero(1, participante_id=10)
    with pytest.raises(ErrorDeValidacionDeDominio):
        a.marcar_pago_numero(1)


@pytest.mark.parametrize("estado", _NO_EDITABLES)
def test_asignar_numero_en_estado_no_editable(estado: EstadoActividad) -> None:
    a = _en_estado_no_editable(estado)
    with pytest.raises(TransicionInvalida):
        a.asignar_numero(4, participante_id=40)


@pytest.mark.parametrize("estado", _NO_EDITABLES)
def test_marcar_pago_en_estado_no_editable(estado: EstadoActividad) -> None:
    a = _en_estado_no_editable(estado)
    with pytest.raises(TransicionInvalida):
        a.marcar_pago_numero(1)


# ===========================================================================
# Movimientos
# ===========================================================================


@pytest.mark.parametrize(
    ("tipo", "valor"),
    [
        (TipoMovimiento.GASTO, "0"),
        (TipoMovimiento.GASTO, "-1"),
        (TipoMovimiento.GASTO, "-5000.50"),
        (TipoMovimiento.INGRESO, "0"),
        (TipoMovimiento.INGRESO, "-0.01"),
        (TipoMovimiento.PREMIO, "-99999.99"),
    ],
)
def test_movimiento_no_positivo_rechazado(
    tipo: TipoMovimiento, valor: str
) -> None:
    """El valor de un movimiento debe ser estrictamente positivo."""
    a = _abierta()
    with pytest.raises(ErrorDeValidacionDeDominio):
        a.registrar_movimiento(tipo, "concepto", Dinero(valor))


@pytest.mark.parametrize(
    "tipo",
    [TipoMovimiento.INGRESO, TipoMovimiento.GASTO, TipoMovimiento.PREMIO],
)
def test_movimiento_positivo_se_registra(tipo: TipoMovimiento) -> None:
    a = _abierta()
    a.registrar_movimiento(tipo, "concepto", Dinero("1234.56"))
    assert len(a.movimientos) == 1
    assert a.movimientos[0].tipo is tipo
    assert a.movimientos[0].valor == Dinero("1234.56")


@pytest.mark.parametrize("estado", _NO_EDITABLES)
def test_registrar_movimiento_en_estado_no_editable(
    estado: EstadoActividad,
) -> None:
    a = _en_estado_no_editable(estado)
    with pytest.raises(TransicionInvalida):
        a.registrar_movimiento(TipoMovimiento.GASTO, "Impresión", Dinero("5000"))


# ===========================================================================
# Cierre
# ===========================================================================


def test_cerrar_abierta_devuelve_utilidad_y_cambia_estado() -> None:
    a = _con_pagados([1, 2])  # 20.000 ingresos, sin sorteo ni gastos
    utilidad = a.cerrar()
    assert utilidad == Dinero("20000.00")
    assert a.estado is EstadoActividad.CERRADA


def test_cerrar_sorteada_devuelve_utilidad_y_cambia_estado() -> None:
    a = _con_pagados([1, 2, 3])  # pozo 30.000
    a.sortear(1, fuente="Lotería")  # premio = pozo -> utilidad 0
    utilidad = a.cerrar()
    assert utilidad == Dinero("0.00")
    assert a.estado is EstadoActividad.CERRADA


@pytest.mark.parametrize("estado", [EstadoActividad.BORRADOR, EstadoActividad.CERRADA])
def test_cerrar_en_estado_invalido(estado: EstadoActividad) -> None:
    if estado is EstadoActividad.BORRADOR:
        a = _nueva()
    else:
        a = _con_pagados([1])
        a.cerrar()  # ya CERRADA
    with pytest.raises(TransicionInvalida):
        a.cerrar()


@pytest.mark.parametrize(
    ("pagados", "gasto", "utilidad_esperada"),
    [
        ([1], "15000", "-5000.00"),
        ([1, 2], "50000", "-30000.00"),
        ([1], "10000.01", "-0.01"),
    ],
)
def test_cerrar_con_utilidad_negativa(
    pagados: list[int], gasto: str, utilidad_esperada: str
) -> None:
    """Gastos > ingresos: utilidad negativa; el dominio la devuelve tal cual
    (el bloqueo por falta de saldo vive en el servicio de aplicación)."""
    a = _con_pagados(pagados)
    a.registrar_movimiento(TipoMovimiento.GASTO, "Impresión", Dinero(gasto))
    utilidad = a.cerrar()
    assert utilidad == Dinero(utilidad_esperada)
    assert utilidad.es_negativo()
    assert a.estado is EstadoActividad.CERRADA


# ===========================================================================
# Clonación (INV-08, RN-049)
# ===========================================================================


def _actividad_completa_con_id(id_: int = 42) -> Actividad:
    """Actividad ABIERTA con números, pagos, sorteo y gastos, con id fijado."""
    a = Actividad(
        TipoActividad.POLLA,
        "Polla de enero",
        periodo_id=1,
        estado=EstadoActividad.ABIERTA,
        valor_numero=Dinero("10000"),
        cantidad_numeros=5,
        id=id_,
    )
    a.asignar_numero(1, participante_id=10)
    a.asignar_numero(2, participante_id=20)
    a.marcar_pago_numero(1)
    a.registrar_movimiento(TipoMovimiento.GASTO, "Impresión", Dinero("3000"))
    a.sortear(1, fuente="Lotería")
    return a


def test_clon_copia_configuracion() -> None:
    a = _actividad_completa_con_id()
    clon = a.clonar_para(periodo_id=2)
    assert clon.tipo is a.tipo
    assert clon.nombre == a.nombre
    assert clon.valor_numero == a.valor_numero
    assert clon.cantidad_numeros == a.cantidad_numeros
    assert clon.periodo_id == 2


def test_clon_copia_numeros_y_participantes() -> None:
    a = _actividad_completa_con_id()
    clon = a.clonar_para(periodo_id=2)
    assert [(n.numero, n.participante_id) for n in clon.numeros] == [(1, 10), (2, 20)]


def test_clon_no_copia_pagos() -> None:
    a = _actividad_completa_con_id()
    clon = a.clonar_para(periodo_id=2)
    assert all(not n.pagado for n in clon.numeros)
    assert clon.numeros_activos() == []
    assert clon.premio_calculado() == Dinero("0.00")


def test_clon_no_copia_sorteo() -> None:
    a = _actividad_completa_con_id()
    assert a.sorteo is not None  # el original sí tiene sorteo
    clon = a.clonar_para(periodo_id=2)
    assert clon.sorteo is None


def test_clon_no_copia_movimientos() -> None:
    a = _actividad_completa_con_id()
    assert a.movimientos != []  # el original tiene ingreso, gasto y premio
    clon = a.clonar_para(periodo_id=2)
    assert clon.movimientos == []
    assert clon.utilidad() == Dinero("0.00")


def test_clon_nace_en_borrador() -> None:
    a = _actividad_completa_con_id()
    clon = a.clonar_para(periodo_id=2)
    assert clon.estado is EstadoActividad.BORRADOR


@pytest.mark.parametrize("id_", [1, 42, 9999])
def test_clon_registra_clonada_de_id(id_: int) -> None:
    a = _actividad_completa_con_id(id_)
    clon = a.clonar_para(periodo_id=2)
    assert clon.clonada_de_id == id_
    assert clon.id is None  # la clonada aún no se persiste


def test_clon_es_independiente_del_original() -> None:
    """Cambiar la clonada no afecta al original ni viceversa."""
    a = _actividad_completa_con_id()
    clon = a.clonar_para(periodo_id=2)
    clon.abrir()
    clon.asignar_numero(3, participante_id=30)
    clon.marcar_pago_numero(3)
    # El original conserva sus 2 números y su sorteo.
    assert [n.numero for n in a.numeros] == [1, 2]
    assert a.sorteo is not None
    assert clon.premio_calculado() == Dinero("10000.00")
