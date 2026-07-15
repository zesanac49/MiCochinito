"""Batería exhaustiva de casos límite y adversariales de los value objects
compartidos (`app.shared.domain`).

Objetivo: cazar errores de redondeo, de tipos y de invariantes de inmutabilidad.
Cada test refleja el comportamiento REAL de la API (leída, no inventada). Los
casos marcados con `xfail` documentan comportamientos sospechosos de ser bugs.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.shared.domain.dinero import MONEDA, Dinero
from app.shared.domain.documento import Documento, TipoDocumento
from app.shared.domain.excepciones import (
    ErrorDeValidacionDeDominio,
    ErrorMonetario,
)
from app.shared.domain.numero_polla import NumeroPolla
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen
from app.shared.domain.tasa import TasaInteres

# ===========================================================================
# Dinero — construcción y tipos
# ===========================================================================


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("0", "0.00"),
        ("0.00", "0.00"),
        ("10", "10.00"),
        ("10.5", "10.50"),
        ("10.50", "10.50"),
        ("-3.14", "-3.14"),
        (0, "0.00"),
        (7, "7.00"),
        (-7, "-7.00"),
        (Decimal("1.23"), "1.23"),
        (Decimal("-1.23"), "-1.23"),
        (Decimal("1"), "1.00"),
    ],
)
def test_dinero_construccion_valida(entrada: object, esperado: str) -> None:
    assert Dinero(entrada).como_str() == esperado  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "valor_float",
    [0.1, 1.0, -2.5, 3.14, 1e10, 0.0, -0.0],
)
def test_dinero_rechaza_float(valor_float: float) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(valor_float)  # type: ignore[arg-type]


@pytest.mark.parametrize("valor_bool", [True, False])
def test_dinero_rechaza_bool(valor_bool: bool) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(valor_bool)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "basura",
    ["abc", "1,23", "", "  ", "1.2.3", "$5", "0x10", None, [], {}, (), b"10"],
)
def test_dinero_rechaza_valores_invalidos(basura: object) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(basura)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "no_finito",
    ["NaN", "-NaN", "Infinity", "-Infinity", "inf", "-inf", "nan"],
)
def test_dinero_rechaza_no_finitos(no_finito: str) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(no_finito)


@pytest.mark.parametrize("no_finito_float", [float("nan"), float("inf"), float("-inf")])
def test_dinero_rechaza_no_finitos_float(no_finito_float: float) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero(no_finito_float)  # type: ignore[arg-type]


# ===========================================================================
# Dinero — redondeo ROUND_HALF_UP exacto
# ===========================================================================


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("0.005", "0.01"),  # tie -> arriba
        ("0.004", "0.00"),  # abajo
        ("0.006", "0.01"),
        ("2.675", "2.68"),  # exacto en Decimal (float fallaría)
        ("1.005", "1.01"),
        ("0.015", "0.02"),
        ("0.025", "0.03"),
        ("0.014", "0.01"),
        ("-0.005", "-0.01"),  # tie negativo -> lejos de cero
        ("-0.006", "-0.01"),
        ("2.344", "2.34"),
        ("2.345", "2.35"),
    ],
)
def test_dinero_redondeo_half_up(entrada: str, esperado: str) -> None:
    assert Dinero(entrada).como_str() == esperado


# ===========================================================================
# Dinero — montos negativos, cero, enormes
# ===========================================================================


@pytest.mark.parametrize(
    ("entrada", "es_cero", "es_pos", "es_neg"),
    [
        ("0.00", True, False, False),
        ("0.001", True, False, False),  # redondea a 0
        ("5.00", False, True, False),
        ("-5.00", False, False, True),
        ("-0.01", False, False, True),
    ],
)
def test_dinero_predicados_signo(
    entrada: str, es_cero: bool, es_pos: bool, es_neg: bool
) -> None:
    d = Dinero(entrada)
    assert d.es_cero() is es_cero
    assert d.es_positivo() is es_pos
    assert d.es_negativo() is es_neg


@pytest.mark.parametrize(
    "grande",
    ["99999999999.99", "1000000000000.00", "-99999999999.99", "123456789012345.67"],
)
def test_dinero_montos_enormes(grande: str) -> None:
    assert Dinero(grande).como_str() == grande


def test_dinero_como_str_siempre_dos_decimales() -> None:
    assert Dinero("5").como_str() == "5.00"
    assert Dinero(Decimal("5.1")).como_str() == "5.10"
    assert Dinero("0").como_str() == "0.00"


def test_dinero_cero_factory() -> None:
    assert Dinero.cero() == Dinero("0")
    assert Dinero.cero().es_cero()


def test_dinero_moneda_es_cop() -> None:
    assert Dinero("1").moneda == MONEDA == "COP"


# ===========================================================================
# Dinero — aritmética entre Dinero
# ===========================================================================


@pytest.mark.parametrize(
    ("a", "b", "suma", "resta"),
    [
        ("10.00", "5.00", "15.00", "5.00"),
        ("0.10", "0.20", "0.30", "-0.10"),
        ("-5.00", "5.00", "0.00", "-10.00"),
        ("99999999999.99", "0.01", "100000000000.00", "99999999999.98"),
        ("0.005", "0.005", "0.02", "0.00"),  # cada operando redondea a 0.01 antes
    ],
)
def test_dinero_suma_resta(a: str, b: str, suma: str, resta: str) -> None:
    da, db = Dinero(a), Dinero(b)
    assert (da + db).como_str() == suma
    assert (da - db).como_str() == resta


@pytest.mark.parametrize(
    ("entrada", "neg", "absol"),
    [
        ("5.00", "-5.00", "5.00"),
        ("-5.00", "5.00", "5.00"),
        ("0.00", "0.00", "0.00"),
    ],
)
def test_dinero_neg_abs(entrada: str, neg: str, absol: str) -> None:
    d = Dinero(entrada)
    assert (-d).como_str() == neg
    assert abs(d).como_str() == absol


@pytest.mark.parametrize("otro", [5, "5.00", 5.0, Decimal("5"), None, True])
def test_dinero_suma_solo_con_dinero(otro: object) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("1.00") + otro  # type: ignore[operator]


@pytest.mark.parametrize("otro", [5, "5.00", Decimal("5"), None])
def test_dinero_resta_solo_con_dinero(otro: object) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("1.00") - otro  # type: ignore[operator]


# ===========================================================================
# Dinero — multiplicado_por
# ===========================================================================


@pytest.mark.parametrize(
    ("base", "factor", "esperado"),
    [
        ("10.00", 3, "30.00"),
        ("10.00", 0, "0.00"),
        ("10.00", -2, "-20.00"),
        ("2.50", 4, "10.00"),
        ("10.00", Decimal("0.333"), "3.33"),
        ("10.00", Decimal("1.5"), "15.00"),
        ("0.01", 100, "1.00"),
        ("100.00", Decimal("0.005"), "0.50"),
        ("3.33", Decimal("0.5"), "1.67"),  # 1.665 -> half up 1.67
    ],
)
def test_dinero_multiplicado_por(base: str, factor: object, esperado: str) -> None:
    assert Dinero(base).multiplicado_por(factor).como_str() == esperado  # type: ignore[arg-type]


@pytest.mark.parametrize("factor", [1.5, True, False, "3", None, [], Decimal("nan")])
def test_dinero_multiplicado_por_rechaza_tipos(factor: object) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("10.00").multiplicado_por(factor)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("base", "factor", "esperado"),
    [("10.00", 3, "30.00"), ("2.00", Decimal("2.5"), "5.00")],
)
def test_dinero_operador_mul(base: str, factor: object, esperado: str) -> None:
    assert (Dinero(base) * factor).como_str() == esperado  # type: ignore[operator]
    assert (factor * Dinero(base)).como_str() == esperado  # rmul  # type: ignore[operator]


# ===========================================================================
# Dinero — dividir_entre
# ===========================================================================


@pytest.mark.parametrize(
    ("base", "divisor", "esperado"),
    [
        ("10.00", 1, "10.00"),
        ("10.00", 2, "5.00"),
        ("10.00", 3, "3.33"),
        ("10.00", 7, "1.43"),
        ("1.00", 3, "0.33"),
        ("0.05", 2, "0.03"),  # 0.025 tie -> half up
        ("100.00", 8, "12.50"),
        ("-10.00", 4, "-2.50"),
        ("7.00", 3, "2.33"),
    ],
)
def test_dinero_dividir_entre(base: str, divisor: int, esperado: str) -> None:
    assert Dinero(base).dividir_entre(divisor).como_str() == esperado


@pytest.mark.parametrize("divisor", [0, -1, -5])
def test_dinero_dividir_entre_no_positivo(divisor: int) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("10.00").dividir_entre(divisor)


@pytest.mark.parametrize("divisor", [2.0, True, False, Decimal("2"), "2", None, 1.5])
def test_dinero_dividir_entre_no_entero(divisor: object) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("10.00").dividir_entre(divisor)  # type: ignore[arg-type]


# ===========================================================================
# Dinero — inmutabilidad
# ===========================================================================


def test_dinero_setattr_lanza() -> None:
    d = Dinero("1.00")
    with pytest.raises(ErrorMonetario):
        d._monto = Decimal("2.00")  # type: ignore[misc]
    with pytest.raises(ErrorMonetario):
        d.otro = 1  # type: ignore[attr-defined]


def test_dinero_delattr_lanza() -> None:
    d = Dinero("1.00")
    with pytest.raises(ErrorMonetario):
        del d._monto  # type: ignore[misc]


# ===========================================================================
# Dinero — igualdad, hash, comparaciones
# ===========================================================================


@pytest.mark.parametrize(
    ("a", "b", "iguales"),
    [
        ("10.00", "10.00", True),
        ("10.00", "10.000", True),  # ambos quantizan a 10.00
        ("10.00", "10.01", False),
        ("0.00", "0", True),
        ("-0.00", "0.00", True),
    ],
)
def test_dinero_igualdad_por_valor(a: str, b: str, iguales: bool) -> None:
    assert (Dinero(a) == Dinero(b)) is iguales
    if iguales:
        assert hash(Dinero(a)) == hash(Dinero(b))


@pytest.mark.parametrize("otro", [10, "10.00", 10.0, None, object()])
def test_dinero_igualdad_con_no_dinero_es_falsa(otro: object) -> None:
    assert Dinero("10.00") != otro
    assert (Dinero("10.00") == otro) is False


def test_dinero_usable_como_clave_de_dict() -> None:
    d = {Dinero("1.00"): "a", Dinero("2.00"): "b"}
    assert d[Dinero("1.00")] == "a"
    assert len(d) == 2


@pytest.mark.parametrize(
    ("a", "b"),
    [("1.00", "2.00"), ("-5.00", "0.00"), ("0.01", "0.02")],
)
def test_dinero_comparaciones_ordinales(a: str, b: str) -> None:
    da, db = Dinero(a), Dinero(b)
    assert da < db
    assert da <= db
    assert db > da
    assert db >= da
    assert not (da > db)


@pytest.mark.parametrize("op", ["lt", "le", "gt", "ge"])
@pytest.mark.parametrize("otro", [5, "5.00", 5.0, None])
def test_dinero_comparaciones_solo_entre_dinero(op: str, otro: object) -> None:
    import operator

    d = Dinero("1.00")
    with pytest.raises(ErrorMonetario):
        getattr(operator, op)(d, otro)


def test_dinero_como_str_negativo_cero_precondicion() -> None:
    """Precondición del bug: -0.004 y 0.004 son iguales por valor y hash."""
    a, b = Dinero("-0.004"), Dinero("0.004")
    assert a == b and hash(a) == hash(b)


def test_dinero_como_str_cero_es_canonico() -> None:
    """El cero es canónico: -0.004 y 0.004 dan ambos '0.00' (sin cero negativo)."""
    a, b = Dinero("-0.004"), Dinero("0.004")
    assert a.como_str() == b.como_str(), (
        f"como_str inconsistente para cero: {a.como_str()!r} != {b.como_str()!r}"
    )


# ===========================================================================
# TasaInteres
# ===========================================================================


@pytest.mark.parametrize(
    ("entrada", "porcentaje"),
    [
        ("2.5", Decimal("2.5")),
        (5, Decimal("5")),
        ("0.01", Decimal("0.01")),
        (Decimal("3.75"), Decimal("3.75")),
        ("100", Decimal("100")),
    ],
)
def test_tasa_construccion_valida(entrada: object, porcentaje: Decimal) -> None:
    assert TasaInteres(entrada).porcentaje == porcentaje  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("entrada", "fraccion"),
    [
        ("2.5", Decimal("0.025")),
        ("100", Decimal("1")),
        ("0.01", Decimal("0.0001")),
        ("50", Decimal("0.5")),
    ],
)
def test_tasa_fraccion(entrada: str, fraccion: Decimal) -> None:
    assert TasaInteres(entrada).fraccion == fraccion


@pytest.mark.parametrize("cero_o_neg", ["0", "0.00", "-1", "-0.01", 0, -5])
def test_tasa_rechaza_cero_o_negativa(cero_o_neg: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(cero_o_neg)  # type: ignore[arg-type]


@pytest.mark.parametrize("basura", [True, False, 1.5, "abc", "", float("nan"), []])
def test_tasa_rechaza_tipos_invalidos(basura: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(basura)  # type: ignore[arg-type]


@pytest.mark.parametrize("basura", [None, {}, object()])
def test_tasa_tipos_no_decimalizables_dan_error_de_dominio(
    basura: object,
) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        TasaInteres(basura)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("valor", "tope", "valida"),
    [
        ("3.0", Decimal("5.0"), True),
        ("5.0", Decimal("5.0"), True),  # igual al tope: permitido
        ("5.01", Decimal("5.0"), False),  # excede
        ("10", Decimal("5"), False),
    ],
)
def test_tasa_tope(valor: str, tope: Decimal, valida: bool) -> None:
    if valida:
        assert TasaInteres(valor, tope=tope).porcentaje == Decimal(valor)
    else:
        with pytest.raises(ErrorDeValidacionDeDominio):
            TasaInteres(valor, tope=tope)


def test_tasa_igualdad_y_hash() -> None:
    assert TasaInteres("2.5") == TasaInteres("2.5")
    assert hash(TasaInteres("2.5")) == hash(TasaInteres("2.5"))
    assert TasaInteres("2.5") != TasaInteres("2.50000001")
    assert TasaInteres("2.5") != "2.5"


def test_tasa_inmutable() -> None:
    t = TasaInteres("2.5")
    with pytest.raises(ErrorDeValidacionDeDominio):
        t._porcentaje = Decimal("9")  # type: ignore[misc]


# ===========================================================================
# Documento
# ===========================================================================


@pytest.mark.parametrize(
    ("tipo", "numero"),
    [
        (TipoDocumento.CC, "12345"),  # min 5 dígitos
        (TipoDocumento.CC, "123456789012345"),  # max 15 dígitos
        (TipoDocumento.CC, "1020304050"),
        (TipoDocumento.CE, "98765"),
        (TipoDocumento.TI, "1122334455"),
        (TipoDocumento.PP, "AB123"),  # alfanumérico min 5
        (TipoDocumento.PP, "abcde"),
        (TipoDocumento.PP, "AB123456789012345678"),  # 20 chars
        (TipoDocumento.CC, "  12345  "),  # se hace strip
    ],
)
def test_documento_valido(tipo: TipoDocumento, numero: str) -> None:
    doc = Documento(tipo, numero)
    assert doc.numero == numero.strip()
    assert doc.tipo is tipo


@pytest.mark.parametrize(
    ("tipo", "numero"),
    [
        (TipoDocumento.CC, "1234"),  # 4 dígitos: corto
        (TipoDocumento.CC, "1234567890123456"),  # 16 dígitos: largo
        (TipoDocumento.CC, "12A45"),  # letra en numérico
        (TipoDocumento.CC, ""),
        (TipoDocumento.CC, "12 34"),  # espacio interno
        (TipoDocumento.CE, "12.34"),
        (TipoDocumento.TI, "-1234"),
        (TipoDocumento.PP, "AB12"),  # 4 chars: corto
        (TipoDocumento.PP, "AB123456789012345678X"),  # 21 chars: largo
        (TipoDocumento.PP, "AB-123"),  # guion no alfanumérico
        (TipoDocumento.PP, "AB 123"),  # espacio interno
    ],
)
def test_documento_formato_invalido(tipo: TipoDocumento, numero: str) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Documento(tipo, numero)


@pytest.mark.parametrize("tipo", ["CC", "cc", 1, None, TipoDocumento])
def test_documento_tipo_invalido(tipo: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Documento(tipo, "12345")  # type: ignore[arg-type]


def test_documento_igualdad_y_hash() -> None:
    a = Documento(TipoDocumento.CC, "12345")
    b = Documento(TipoDocumento.CC, "12345")
    c = Documento(TipoDocumento.CE, "12345")
    assert a == b and hash(a) == hash(b)
    assert a != c
    assert a != "12345"


def test_documento_inmutable() -> None:
    doc = Documento(TipoDocumento.CC, "12345")
    with pytest.raises(ErrorDeValidacionDeDominio):
        doc._numero = "999"  # type: ignore[misc]


# ===========================================================================
# NumeroPolla
# ===========================================================================


@pytest.mark.parametrize(
    ("valor", "cantidad"),
    [
        (1, 1),  # límite inferior == superior
        (1, 100),
        (100, 100),  # límite superior
        (50, 100),
        (99, 100),
    ],
)
def test_numero_polla_valido(valor: int, cantidad: int) -> None:
    assert NumeroPolla(valor, cantidad).valor == valor


@pytest.mark.parametrize(
    ("valor", "cantidad"),
    [
        (0, 100),  # bajo el mínimo
        (-1, 100),
        (101, 100),  # sobre el máximo
        (2, 1),
        (1, 0),  # cantidad 0 => rango vacío
    ],
)
def test_numero_polla_fuera_de_rango(valor: int, cantidad: int) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        NumeroPolla(valor, cantidad)


@pytest.mark.parametrize("valor", [True, False, 1.0, "1", None, Decimal("1")])
def test_numero_polla_rechaza_no_entero(valor: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        NumeroPolla(valor, 100)  # type: ignore[arg-type]


def test_numero_polla_igualdad_y_hash() -> None:
    assert NumeroPolla(5, 100) == NumeroPolla(5, 100)
    assert hash(NumeroPolla(5, 100)) == hash(NumeroPolla(5, 100))
    assert NumeroPolla(5, 100) != NumeroPolla(6, 100)
    assert NumeroPolla(5, 100) != 5


def test_numero_polla_inmutable() -> None:
    n = NumeroPolla(5, 100)
    with pytest.raises(ErrorDeValidacionDeDominio):
        n._valor = 9  # type: ignore[misc]


# ===========================================================================
# ReferenciaOrigen
# ===========================================================================


@pytest.mark.parametrize("tipo", list(TipoOrigen))
def test_referencia_valida_todos_los_tipos(tipo: TipoOrigen) -> None:
    ref = ReferenciaOrigen(tipo, 1)
    assert ref.tipo is tipo
    assert ref.id_origen == 1


@pytest.mark.parametrize("id_origen", [0, -1, -100, True, False, 1.0, "1", None])
def test_referencia_id_invalido(id_origen: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        ReferenciaOrigen(TipoOrigen.CUOTA, id_origen)  # type: ignore[arg-type]


@pytest.mark.parametrize("tipo", ["CUOTA", 1, None, TipoOrigen])
def test_referencia_tipo_invalido(tipo: object) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        ReferenciaOrigen(tipo, 1)  # type: ignore[arg-type]


def test_referencia_igualdad_y_hash() -> None:
    a = ReferenciaOrigen(TipoOrigen.PRESTAMO, 7)
    b = ReferenciaOrigen(TipoOrigen.PRESTAMO, 7)
    c = ReferenciaOrigen(TipoOrigen.MULTA, 7)
    assert a == b and hash(a) == hash(b)
    assert a != c
    assert a != 7


def test_referencia_inmutable() -> None:
    ref = ReferenciaOrigen(TipoOrigen.CUOTA, 1)
    with pytest.raises(ErrorDeValidacionDeDominio):
        ref._id = 2  # type: ignore[misc]
