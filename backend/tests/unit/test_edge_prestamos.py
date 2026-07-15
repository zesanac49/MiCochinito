"""Casos borde EXHAUSTIVOS del agregado `Prestamo` (dominio puro, RN-030..038, INV-04).

Todas las fechas se controlan explícitamente. Modelo de interés simple:
- `desembolsar(fecha)` cobra el primer mes de interés y adelanta el reloj un mes
  (`fecha_ultimo_calculo = fecha + 1 mes`).
- `interes_pendiente(hasta)` = interés ya acumulado + meses completos transcurridos
  desde `fecha_ultimo_calculo` × saldo × tasa.

Consecuencia (verificada, no es bug): a N meses del desembolso el interés pendiente
equivale a `max(N, 1)` meses, porque el primer mes se cobra en el desembolso.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.modules.prestamos.domain.estados import EstadoPrestamo as E
from app.modules.prestamos.domain.excepciones import PagoInvalido
from app.modules.prestamos.domain.prestamo import Prestamo, _sumar_meses
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import TransicionInvalida
from app.shared.domain.tasa import TasaInteres

_F = date(2026, 1, 15)  # fecha canónica de desembolso (día 15)


# --------------------------------------------------------------------------- #
# Fábricas de préstamos en distintos estados (vía API pública)
# --------------------------------------------------------------------------- #
def _solicitado(capital: str = "1000000", tasa: str = "2") -> Prestamo:
    return Prestamo.solicitar(1, Dinero(capital), TasaInteres(Decimal(tasa)), plazo_meses=12)


def _aprobado(capital: str = "1000000", tasa: str = "2") -> Prestamo:
    p = _solicitado(capital, tasa)
    p.aprobar()
    return p


def _rechazado(capital: str = "1000000", tasa: str = "2") -> Prestamo:
    p = _solicitado(capital, tasa)
    p.rechazar("sin capacidad")
    return p


def _en_pago(capital: str = "1000000", tasa: str = "2", fecha: date = _F) -> Prestamo:
    p = _aprobado(capital, tasa)
    p.desembolsar(fecha)
    return p


def _en_mora(capital: str = "1000000", tasa: str = "2", fecha: date = _F) -> Prestamo:
    p = _en_pago(capital, tasa, fecha)
    p.marcar_mora()
    return p


def _pagado(capital: str = "1000000", tasa: str = "2", fecha: date = _F) -> Prestamo:
    p = _en_pago(capital, tasa, fecha)
    adeudado = p.saldo_capital + p.interes_pendiente(fecha)
    p.registrar_pago(adeudado, fecha)
    assert p.estado is E.PAGADO
    return p


# --------------------------------------------------------------------------- #
# 1. Desembolso: cobra el primer mes y fija el reloj
# --------------------------------------------------------------------------- #
def test_desembolso_cobra_primer_mes_y_fija_reloj() -> None:
    p = _en_pago("1000000", "2", _F)
    assert p.estado is E.EN_PAGO
    assert p.saldo_capital == Dinero("1000000.00")
    assert p.fecha_desembolso == _F
    assert p.interes_acumulado == Dinero("20000.00")  # 1.000.000 × 2%
    assert p.fecha_ultimo_calculo == date(2026, 2, 15)  # _F + 1 mes


# --------------------------------------------------------------------------- #
# 2. Interés por meses transcurridos (capital × tasa × meses)
# --------------------------------------------------------------------------- #
# (capital, tasa%, interés mensual exacto)
_CASOS_INTERES = [
    ("1000000", "2", "20000"),
    ("500000", "1.5", "7500"),
    ("2000000", "3", "60000"),
    ("1200000", "2.5", "30000"),
    ("750000", "2", "15000"),
]


@pytest.mark.parametrize("capital,tasa,mensual", _CASOS_INTERES)
@pytest.mark.parametrize("meses", [0, 1, 3, 6, 12])
def test_interes_pendiente_por_meses(capital: str, tasa: str, mensual: str, meses: int) -> None:
    """A N meses del desembolso el pendiente = max(N, 1) × interés mensual."""
    p = _en_pago(capital, tasa, _F)
    hasta = _sumar_meses(_F, meses)
    esperado = Dinero(mensual).multiplicado_por(max(meses, 1))
    assert p.interes_pendiente(hasta) == esperado


def test_interes_pendiente_no_muta_el_agregado() -> None:
    p = _en_pago("1000000", "2", _F)
    antes = p.interes_acumulado
    p.interes_pendiente(_sumar_meses(_F, 6))
    assert p.interes_acumulado == antes  # consulta pura, sin devengar


# --------------------------------------------------------------------------- #
# 3. Mes parcial: día < día de desembolso no cuenta como mes completo
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "hasta,meses_esperados",
    [
        (date(2026, 3, 14), 1),  # un día antes del corte → aún 1 mes (el del desembolso)
        (date(2026, 3, 15), 2),  # justo el corte → 2 meses
        (date(2026, 3, 16), 2),  # un día después → sigue 2 meses
        (date(2026, 4, 14), 2),  # casi 3 meses pero día 14 < 15 → 2
        (date(2026, 4, 15), 3),  # corte exacto → 3
    ],
)
def test_mes_parcial(hasta: date, meses_esperados: int) -> None:
    p = _en_pago("1000000", "2", _F)  # interés mensual = 20.000
    assert p.interes_pendiente(hasta) == Dinero("20000").multiplicado_por(meses_esperados)


# --------------------------------------------------------------------------- #
# 4. Cruce de año
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "desembolso,hasta,meses_esperados",
    [
        (date(2026, 11, 15), date(2027, 2, 15), 3),   # nov→feb del año siguiente
        (date(2026, 12, 15), date(2027, 1, 15), 1),   # dic→ene (solo el mes de desembolso)
        (date(2026, 12, 15), date(2027, 3, 15), 3),   # dic→mar
        # desembolso día 30 → reloj en dic-30; feb-28 < día 30 no cierra el mes → 2 meses
        (date(2026, 11, 30), date(2027, 2, 28), 2),
    ],
)
def test_cruce_de_anio(desembolso: date, hasta: date, meses_esperados: int) -> None:
    p = _en_pago("1000000", "2", desembolso)
    assert p.interes_pendiente(hasta) == Dinero("20000").multiplicado_por(meses_esperados)


# --------------------------------------------------------------------------- #
# 5. registrar_pago: descomposición interés-primero
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "monto,interes_esp,capital_esp,saldo_esp",
    [
        ("20000", "20000.00", "0.00", "1000000.00"),      # solo interés
        ("15000", "15000.00", "0.00", "1000000.00"),      # parcial de interés
        ("120000", "20000.00", "100000.00", "900000.00"), # interés + capital
        ("520000", "20000.00", "500000.00", "500000.00"), # interés + medio capital
        ("1", "1.00", "0.00", "1000000.00"),              # mínimo, todo a interés
    ],
)
def test_pago_descomposicion(
    monto: str, interes_esp: str, capital_esp: str, saldo_esp: str
) -> None:
    p = _en_pago("1000000", "2", _F)  # interés acumulado = 20.000
    desc = p.registrar_pago(Dinero(monto), _F)
    assert desc.interes == Dinero(interes_esp)
    assert desc.capital == Dinero(capital_esp)
    assert desc.total == Dinero(monto)          # RN-033 exacto
    assert p.saldo_capital == Dinero(saldo_esp)


def test_pago_parcial_deja_interes_acumulado() -> None:
    p = _en_pago("1000000", "2", _F)  # interés = 20.000
    p.registrar_pago(Dinero("15000"), _F)
    assert p.interes_acumulado == Dinero("5000.00")  # queda interés pendiente
    assert p.saldo_capital == Dinero("1000000.00")   # capital intacto


def test_pago_solo_interes_no_abona_capital() -> None:
    p = _en_pago("1000000", "2", _F)
    p.registrar_pago(Dinero("20000"), _F)
    assert p.interes_acumulado.es_cero()
    assert p.saldo_capital == Dinero("1000000.00")
    assert p.estado is E.EN_PAGO  # no queda saldado


# --------------------------------------------------------------------------- #
# 6. PAGADO solo cuando saldo Y interés están en cero
# --------------------------------------------------------------------------- #
def test_pago_total_marca_pagado() -> None:
    p = _en_pago("1000000", "2", _F)
    p.registrar_pago(Dinero("1020000"), _F)  # 1.000.000 + 20.000
    assert p.estado is E.PAGADO
    assert p.saldo_capital.es_cero()
    assert p.interes_acumulado.es_cero()


@pytest.mark.parametrize("monto", ["20000", "120000", "1019999", "1000000"])
def test_pago_incompleto_no_marca_pagado(monto: str) -> None:
    p = _en_pago("1000000", "2", _F)  # adeudado = 1.020.000
    p.registrar_pago(Dinero(monto), _F)
    assert p.estado is E.EN_PAGO
    assert not (p.saldo_capital.es_cero() and p.interes_acumulado.es_cero())


def test_pagado_requiere_dos_condiciones_en_cero() -> None:
    """Pagar todo menos 1 peso de capital deja saldo>0 y NO marca PAGADO."""
    p = _en_pago("1000000", "2", _F)  # adeudado = 1.020.000
    p.registrar_pago(Dinero("1019999"), _F)
    assert p.saldo_capital == Dinero("1.00")
    assert p.interes_acumulado.es_cero()
    assert p.estado is E.EN_PAGO
    p.registrar_pago(Dinero("1"), _F)  # salda el último peso
    assert p.estado is E.PAGADO


# --------------------------------------------------------------------------- #
# 7. Pagos inválidos → PagoInvalido
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("monto", ["1020000.01", "1020001", "2000000", "5000000"])
def test_pago_excede_adeudado(monto: str) -> None:
    p = _en_pago("1000000", "2", _F)  # adeudado a la fecha = 1.020.000
    with pytest.raises(PagoInvalido):
        p.registrar_pago(Dinero(monto), _F)


def test_pago_excede_adeudado_a_fecha_futura() -> None:
    """El adeudado crece con los meses; el tope de validación se mueve con él."""
    p = _en_pago("1000000", "2", _F)
    hasta = _sumar_meses(_F, 3)  # adeudado = 1.000.000 + 60.000
    with pytest.raises(PagoInvalido):
        p.registrar_pago(Dinero("1060000.01"), hasta)
    # justo el adeudado sí es válido y liquida
    p.registrar_pago(Dinero("1060000"), hasta)
    assert p.estado is E.PAGADO


@pytest.mark.parametrize("monto", ["0", "-1", "-100000", "-0.01"])
def test_pago_no_positivo(monto: str) -> None:
    p = _en_pago("1000000", "2", _F)
    with pytest.raises(PagoInvalido):
        p.registrar_pago(Dinero(monto), _F)


# --------------------------------------------------------------------------- #
# 8. Pagar en estados no permitidos → TransicionInvalida
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "factory,estado",
    [
        (_solicitado, E.SOLICITADO),
        (_aprobado, E.APROBADO),
        (_rechazado, E.RECHAZADO),
        (_pagado, E.PAGADO),
    ],
)
def test_pagar_en_estado_no_permitido(factory, estado: E) -> None:  # type: ignore[no-untyped-def]
    p = factory()
    assert p.estado is estado
    with pytest.raises(TransicionInvalida):
        p.registrar_pago(Dinero("1000"), _F)


@pytest.mark.parametrize("factory", [_en_pago, _en_mora])
def test_pagar_en_estado_permitido(factory) -> None:  # type: ignore[no-untyped-def]
    p = factory()
    desc = p.registrar_pago(Dinero("20000"), _F)
    assert desc.interes == Dinero("20000.00")


# --------------------------------------------------------------------------- #
# 9. Pagos en varios meses: el devengo acumula entre pagos
# --------------------------------------------------------------------------- #
def test_devengo_acumula_entre_pagos_separados_por_meses() -> None:
    p = _en_pago("1000000", "2", _F)          # interés mes 1 = 20.000
    p.registrar_pago(Dinero("20000"), _F)     # salda interés, capital intacto
    assert p.interes_acumulado.es_cero()
    hasta = _sumar_meses(_F, 3)               # transcurren 2 meses más → 40.000
    assert p.interes_pendiente(hasta) == Dinero("40000.00")
    desc = p.registrar_pago(Dinero("40000"), hasta)
    assert desc.interes == Dinero("40000.00")
    assert desc.capital.es_cero()
    assert p.saldo_capital == Dinero("1000000.00")


def test_devengo_sobre_saldo_reducido() -> None:
    """Tras abonar capital, el interés siguiente se calcula sobre el saldo menor."""
    p = _en_pago("1000000", "2", _F)
    p.registrar_pago(Dinero("520000"), _F)     # interés 20.000 + capital 500.000
    assert p.saldo_capital == Dinero("500000.00")
    hasta = _sumar_meses(_F, 2)                # 1 mes más sobre 500.000 → 10.000
    assert p.interes_pendiente(hasta) == Dinero("10000.00")


@pytest.mark.parametrize("chunk", ["100000", "250000", "333333"])
def test_liquidacion_multi_mes_capital_retorna_integro(chunk: str) -> None:
    """INV-04: Σ capital pagado == capital original, avanzando un mes por pago."""
    capital0 = Dinero("1000000")
    p = _en_pago("1000000", "2", _F)
    acumulado = Dinero.cero()
    fecha = _F
    guarda = 0
    trozo = Dinero(chunk)
    while p.estado is not E.PAGADO and guarda < 500:
        guarda += 1
        interes = p.interes_pendiente(fecha)
        # liquida el saldo restante o abona un trozo de capital
        monto = (p.saldo_capital + interes) if p.saldo_capital <= trozo else (interes + trozo)
        desc = p.registrar_pago(monto, fecha)
        assert desc.capital + desc.interes == monto
        acumulado = acumulado + desc.capital
        fecha = _sumar_meses(fecha, 1)
    assert p.estado is E.PAGADO
    assert acumulado == capital0


# --------------------------------------------------------------------------- #
# 10. Máquina de estados: transiciones válidas
# --------------------------------------------------------------------------- #
def test_transiciones_validas_camino_feliz() -> None:
    p = _solicitado()
    assert p.estado is E.SOLICITADO
    p.aprobar()
    assert p.estado is E.APROBADO
    p.desembolsar(_F)
    assert p.estado is E.EN_PAGO
    p.marcar_mora()
    assert p.estado is E.EN_MORA
    p.regularizar()
    assert p.estado is E.EN_PAGO


def test_rechazo_desde_solicitado() -> None:
    p = _solicitado()
    p.rechazar("motivo x")
    assert p.estado is E.RECHAZADO
    assert p.motivo_rechazo == "motivo x"


def test_pago_desde_mora_marca_pagado() -> None:
    p = _en_mora("1000000", "2", _F)
    p.registrar_pago(Dinero("1020000"), _F)
    assert p.estado is E.PAGADO


# --------------------------------------------------------------------------- #
# 11. Máquina de estados: transiciones inválidas → TransicionInvalida
# --------------------------------------------------------------------------- #
_ACC_APROBAR = ("aprobar", lambda p: p.aprobar())
_ACC_RECHAZAR = ("rechazar", lambda p: p.rechazar("x"))
_ACC_DESEMBOLSAR = ("desembolsar", lambda p: p.desembolsar(_F))
_ACC_MORA = ("marcar_mora", lambda p: p.marcar_mora())
_ACC_REGULARIZAR = ("regularizar", lambda p: p.regularizar())


@pytest.mark.parametrize(
    "factory,accion",
    [
        # Desde SOLICITADO
        (_solicitado, _ACC_DESEMBOLSAR),   # no se desembolsa sin aprobar
        (_solicitado, _ACC_MORA),
        (_solicitado, _ACC_REGULARIZAR),
        # Desde APROBADO
        (_aprobado, _ACC_APROBAR),         # aprobar dos veces
        (_aprobado, _ACC_RECHAZAR),        # rechazar un aprobado
        (_aprobado, _ACC_MORA),
        (_aprobado, _ACC_REGULARIZAR),
        # Desde RECHAZADO (estado terminal)
        (_rechazado, _ACC_APROBAR),        # aprobar un rechazado
        (_rechazado, _ACC_RECHAZAR),
        (_rechazado, _ACC_DESEMBOLSAR),
        # Desde EN_PAGO
        (_en_pago, _ACC_APROBAR),
        (_en_pago, _ACC_DESEMBOLSAR),      # desembolsar dos veces
        (_en_pago, _ACC_REGULARIZAR),      # regularizar sin mora
        # Desde EN_MORA
        (_en_mora, _ACC_MORA),             # ya está en mora
        (_en_mora, _ACC_DESEMBOLSAR),
        (_en_mora, _ACC_APROBAR),
        # Desde PAGADO (estado terminal)
        (_pagado, _ACC_MORA),
        (_pagado, _ACC_APROBAR),
        (_pagado, _ACC_DESEMBOLSAR),
    ],
    ids=lambda v: v[0] if isinstance(v, tuple) else getattr(v, "__name__", str(v)),
)
def test_transiciones_invalidas(factory, accion) -> None:  # type: ignore[no-untyped-def]
    _nombre, op = accion
    p = factory()
    with pytest.raises(TransicionInvalida):
        op(p)


# --------------------------------------------------------------------------- #
# 12. Property test: INV-04 con fechas avanzando y capitales/tasas aleatorios
# --------------------------------------------------------------------------- #
_capitales = st.decimals(
    min_value=Decimal("10000.00"), max_value=Decimal("5000000.00"), places=2,
    allow_nan=False, allow_infinity=False,
)
_tasas = st.decimals(
    min_value=Decimal("0.5"), max_value=Decimal("3.0"), places=2,
    allow_nan=False, allow_infinity=False,
)


@settings(max_examples=50, deadline=None)
@given(_capitales, _tasas)
def test_prop_inv_04_capital_integro_fechas_avanzando(capital: Decimal, tasa: Decimal) -> None:
    p = _en_pago(str(capital), str(tasa), _F)
    acumulado = Dinero.cero()
    fecha = _F
    trozo = Dinero("50000")
    guarda = 0
    while p.estado is not E.PAGADO and guarda < 500:
        guarda += 1
        interes = p.interes_pendiente(fecha)
        monto = (p.saldo_capital + interes) if p.saldo_capital <= trozo else (interes + trozo)
        desc = p.registrar_pago(monto, fecha)
        assert desc.capital + desc.interes == monto
        acumulado = acumulado + desc.capital
        fecha = _sumar_meses(fecha, 1)
    assert p.estado is E.PAGADO
    assert acumulado == Dinero(capital)
