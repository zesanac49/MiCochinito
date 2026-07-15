"""Casos borde exhaustivos del núcleo contable (INV-01..03/11/12, RN-007/061/063).

Cubre, sin base de datos (fakes en memoria para los puertos de aplicación):

* Matriz concepto × fondo × naturaleza: TODAS las combinaciones válidas
  aceptadas y todas las inválidas (fondo o naturaleza equivocados) rechazadas
  con `ViolacionSeparacionDeFondos`.
* `Asiento`: monto cero/negativo e inválido rechazados, descripción obligatoria,
  inmutabilidad e igualdad estructural, REVERSION exige `reversa_de_id`.
* Saldo derivado del ledger (Σ créditos − Σ débitos), por fondo y por
  participante, y secuencias de asientos.
* Reversión: asiento espejo invierte la naturaleza, el saldo vuelve, y el
  comportamiento actual ante doble reversión.
* Reconciliación: caché que cuadra vs. descuadre detectado (con auditoría).
* Saldo insuficiente en egresos (RN-007), incluido el límite exacto a cero.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.reconciliacion import ServicioReconciliacion
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable as C,
)
from app.modules.contabilidad.domain.conceptos import (
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import (
    SaldoInsuficiente,
    ViolacionSeparacionDeFondos,
)
from app.modules.contabilidad.domain.fondo import Fondo
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, ErrorMonetario
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen

D = Naturaleza.DEBITO
Cr = Naturaleza.CREDITO
AHORRO = TipoFondo.AHORRO
RENT = TipoFondo.RENTABILIDAD

_OTRO_FONDO = {AHORRO: RENT, RENT: AHORRO}


def _opuesta(n: Naturaleza) -> Naturaleza:
    return D if n is Cr else Cr


_REF = ReferenciaOrigen(TipoOrigen.CUOTA, 1)


def _asiento(
    concepto: C,
    fondo: TipoFondo,
    naturaleza: Naturaleza,
    *,
    monto: str = "1000",
    participante_id: int | None = None,
    reversa_de_id: int | None = None,
) -> Asiento:
    return Asiento(
        monto=Dinero(monto),
        naturaleza=naturaleza,
        concepto=concepto,
        fondo=fondo,
        referencia=_REF,
        descripcion="prueba",
        participante_id=participante_id,
        reversa_de_id=reversa_de_id,
    )


# ---------------------------------------------------------------------------
# Datos de la matriz de separación de fondos (doc 02 §5). Escritos a mano para
# que el test verifique el invariante y no sea un espejo de la implementación.
# ---------------------------------------------------------------------------

VALID_COMBOS: list[tuple[C, TipoFondo, Naturaleza]] = [
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
]

# Naturaleza equivocada sobre el fondo correcto (el concepto sí puede tocarlo).
WRONG_NATURALEZA: list[tuple[C, TipoFondo, Naturaleza]] = [
    (c, f, _opuesta(n)) for c, f, n in VALID_COMBOS
]

# Fondo equivocado: el concepto no puede afectar el otro fondo (matriz = None),
# con cualquiera de las dos naturalezas.
WRONG_FONDO: list[tuple[C, TipoFondo, Naturaleza]] = [
    (c, _OTRO_FONDO[f], nat) for c, f, _ in VALID_COMBOS for nat in (D, Cr)
]


# ---------------------------------------------------------------------------
# INV-01..03 — matriz concepto ↔ fondo ↔ naturaleza
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("concepto", "fondo", "naturaleza"), VALID_COMBOS)
def test_matriz_combinacion_valida_aceptada(
    concepto: C, fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    Fondo(fondo, natillera_id=1).validar_asiento(_asiento(concepto, fondo, naturaleza))


@pytest.mark.parametrize(("concepto", "fondo", "naturaleza"), WRONG_NATURALEZA)
def test_matriz_naturaleza_equivocada_rechazada(
    concepto: C, fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    with pytest.raises(ViolacionSeparacionDeFondos):
        Fondo(fondo, natillera_id=1).validar_asiento(_asiento(concepto, fondo, naturaleza))


@pytest.mark.parametrize(("concepto", "fondo", "naturaleza"), WRONG_FONDO)
def test_matriz_fondo_equivocado_rechazado(
    concepto: C, fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    # El concepto no puede afectar este fondo (celda None de la matriz).
    with pytest.raises(ViolacionSeparacionDeFondos):
        Fondo(fondo, natillera_id=1).validar_asiento(_asiento(concepto, fondo, naturaleza))


@pytest.mark.parametrize(("concepto", "fondo", "naturaleza"), VALID_COMBOS)
def test_inv_01_asiento_validado_por_el_otro_fondo_es_rechazado(
    concepto: C, fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    # Asiento correcto para su fondo, pero validado por el agregado del otro
    # fondo: primer guardia de `validar_asiento` (fondo distinto).
    otro = Fondo(_OTRO_FONDO[fondo], natillera_id=1)
    with pytest.raises(ViolacionSeparacionDeFondos):
        otro.validar_asiento(_asiento(concepto, fondo, naturaleza))


# ---------------------------------------------------------------------------
# REVERSION — espejo, válida sobre cualquier fondo/naturaleza si referencia
# el asiento revertido (RN-061)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fondo", [AHORRO, RENT])
@pytest.mark.parametrize("naturaleza", [D, Cr])
def test_reversion_con_referencia_es_valida(
    fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    Fondo(fondo, natillera_id=1).validar_asiento(
        _asiento(C.REVERSION, fondo, naturaleza, reversa_de_id=42)
    )


@pytest.mark.parametrize("fondo", [AHORRO, RENT])
@pytest.mark.parametrize("naturaleza", [D, Cr])
def test_reversion_sin_referencia_es_rechazada(
    fondo: TipoFondo, naturaleza: Naturaleza
) -> None:
    with pytest.raises(ViolacionSeparacionDeFondos):
        Fondo(fondo, natillera_id=1).validar_asiento(
            _asiento(C.REVERSION, fondo, naturaleza)
        )


def test_reversion_a_fondo_distinto_del_validador_es_rechazada() -> None:
    reverso = _asiento(C.REVERSION, AHORRO, Cr, reversa_de_id=42)
    with pytest.raises(ViolacionSeparacionDeFondos):
        Fondo(RENT, natillera_id=1).validar_asiento(reverso)


# ---------------------------------------------------------------------------
# Asiento — invariantes de construcción (INV-11)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("monto", ["0", "0.00", "-1", "-1000.50", "-0.01"])
def test_asiento_monto_no_positivo_rechazado(monto: str) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        _asiento(C.CUOTA_AHORRO, AHORRO, Cr, monto=monto)


@pytest.mark.parametrize("descripcion", ["", "   ", "\t\n"])
def test_asiento_requiere_descripcion(descripcion: str) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Asiento(
            monto=Dinero("1000"),
            naturaleza=Cr,
            concepto=C.CUOTA_AHORRO,
            fondo=AHORRO,
            referencia=_REF,
            descripcion=descripcion,
        )


def test_asiento_monto_debe_ser_dinero_no_decimal_ni_int() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Asiento(
            monto=1000,  # type: ignore[arg-type]
            naturaleza=Cr,
            concepto=C.CUOTA_AHORRO,
            fondo=AHORRO,
            referencia=_REF,
            descripcion="prueba",
        )


def test_asiento_monto_desde_float_es_rechazado_por_dinero() -> None:
    # TEC-01: Dinero prohíbe construir desde float (antes de llegar al Asiento).
    with pytest.raises(ErrorMonetario):
        Dinero(1000.0)  # type: ignore[arg-type]


def test_asiento_es_inmutable() -> None:
    a = _asiento(C.CUOTA_AHORRO, AHORRO, Cr)
    with pytest.raises(FrozenInstanceError):
        a.monto = Dinero("2000")  # type: ignore[misc]


def test_asiento_igualdad_estructural() -> None:
    a = _asiento(C.CUOTA_AHORRO, AHORRO, Cr, participante_id=5)
    b = _asiento(C.CUOTA_AHORRO, AHORRO, Cr, participante_id=5)
    c = _asiento(C.CUOTA_AHORRO, AHORRO, Cr, participante_id=6)
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# Saldo derivado (RN-063, INV-12): Σ créditos − Σ débitos
# ---------------------------------------------------------------------------


def _mov(naturaleza: Naturaleza, monto: str, participante_id: int | None = None) -> Asiento:
    return _asiento(
        C.CUOTA_AHORRO, AHORRO, naturaleza, monto=monto, participante_id=participante_id
    )


def test_saldo_vacio_es_cero() -> None:
    assert Fondo.saldo([]) == Dinero.cero()


@pytest.mark.parametrize(
    ("movimientos", "esperado"),
    [
        ([(Cr, "1000.00")], "1000.00"),
        ([(Cr, "1000.00"), (Cr, "500.00")], "1500.00"),
        ([(Cr, "1000.00"), (D, "300.00")], "700.00"),
        ([(Cr, "1000.00"), (D, "1000.00")], "0.00"),
        ([(D, "250.00")], "-250.00"),
        ([(Cr, "0.01"), (Cr, "0.02")], "0.03"),
        ([(Cr, "1000.00"), (D, "300.00"), (Cr, "50.00"), (D, "50.00")], "700.00"),
    ],
)
def test_saldo_secuencia_de_asientos(
    movimientos: list[tuple[Naturaleza, str]], esperado: str
) -> None:
    asientos = [_mov(nat, monto) for nat, monto in movimientos]
    assert Fondo.saldo(asientos) == Dinero(esperado)


def test_saldo_por_participante_via_servicio() -> None:
    svc, _, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "1000.00", participante_id=7), creado_por=1)
    svc.registrar_asiento(_mov(Cr, "500.00", participante_id=7), creado_por=1)
    # Débito a Ahorro con un concepto válido (DEVOLUCION_AHORRO), ya con saldo.
    svc.registrar_asiento(
        _asiento(C.DEVOLUCION_AHORRO, AHORRO, D, monto="200.00", participante_id=7),
        creado_por=1,
    )
    svc.registrar_asiento(_mov(Cr, "999.00", participante_id=8), creado_por=1)
    assert svc.saldo_participante(7, AHORRO) == Dinero("1300.00")
    assert svc.saldo_participante(8, AHORRO) == Dinero("999.00")
    assert svc.saldo_participante(999, AHORRO) == Dinero.cero()


# ---------------------------------------------------------------------------
# Fakes en memoria de los puertos de aplicación
# ---------------------------------------------------------------------------


class LedgerFake:
    """Ledger append-only en memoria (implementa RepositorioLedger)."""

    def __init__(self) -> None:
        self._asientos: list[AsientoLeido] = []
        self._seq = 0

    def append(self, asiento: Asiento, fondo_id: int, creado_por: int) -> AsientoLeido:
        self._seq += 1
        leido = AsientoLeido(
            uuid=f"uuid-{self._seq}",
            creado_en=datetime.now(UTC),
            fondo=asiento.fondo,
            naturaleza=asiento.naturaleza,
            concepto=asiento.concepto,
            monto=asiento.monto,
            descripcion=asiento.descripcion,
            origen_tipo=asiento.referencia.tipo.value,
            origen_id=asiento.referencia.id_origen,
            participante_id=asiento.participante_id,
            id=self._seq,
        )
        self._asientos.append(leido)
        return leido

    def obtener_por_uuid(self, uuid: str) -> AsientoLeido | None:
        return next((a for a in self._asientos if a.uuid == uuid), None)

    def listar(
        self,
        *,
        fondo: TipoFondo | None = None,
        concepto: C | None = None,
        participante_id: int | None = None,
    ) -> list[AsientoLeido]:
        res = list(self._asientos)
        if fondo is not None:
            res = [a for a in res if a.fondo is fondo]
        if concepto is not None:
            res = [a for a in res if a.concepto is concepto]
        if participante_id is not None:
            res = [a for a in res if a.participante_id == participante_id]
        return res


class FondosFake:
    """Fondos en memoria; el saldo se deriva del ledger (implementa
    RepositorioFondos y LecturaFondos)."""

    def __init__(self, ledger: LedgerFake) -> None:
        self._ledger = ledger
        self._ids = {AHORRO: 1, RENT: 2}
        self._cache = {AHORRO: Dinero.cero(), RENT: Dinero.cero()}

    def crear_par(self) -> None:  # pragma: no cover - no usado en estos tests
        pass

    def existe_par(self) -> bool:
        return True

    def id_de(self, tipo: TipoFondo) -> int | None:
        return self._ids[tipo]

    def cargar(self, tipo: TipoFondo) -> Fondo:
        return Fondo(tipo, natillera_id=1, id=self._ids[tipo])

    def saldo(self, tipo: TipoFondo) -> Dinero:
        total = Dinero.cero()
        for a in self._ledger.listar(fondo=tipo):
            total = total + a.monto if a.naturaleza is Cr else total - a.monto
        return total

    def saldo_cache(self, tipo: TipoFondo) -> Dinero:
        return self._cache[tipo]

    def actualizar_cache(self, tipo: TipoFondo, saldo: Dinero) -> None:
        self._cache[tipo] = saldo


class AuditoriaFake:
    def __init__(self) -> None:
        self.registros: list[tuple[int, str, str, int | None, dict | None]] = []

    def registrar(
        self,
        usuario_id: int,
        accion: str,
        entidad_tipo: str,
        entidad_id: int | None = None,
        detalle: dict[str, object] | None = None,
    ) -> None:
        self.registros.append((usuario_id, accion, entidad_tipo, entidad_id, detalle))


def _servicio() -> tuple[ServicioContabilidad, FondosFake, LedgerFake]:
    ledger = LedgerFake()
    fondos = FondosFake(ledger)
    return ServicioContabilidad(fondos, ledger), fondos, ledger


# ---------------------------------------------------------------------------
# Servicio — registro, caché reconciliable y saldo no negativo (RN-007)
# ---------------------------------------------------------------------------


def test_registrar_asiento_actualiza_cache_reconciliable() -> None:
    svc, fondos, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "1000.00"), creado_por=1)
    assert fondos.saldo(AHORRO) == Dinero("1000.00")
    assert fondos.saldo_cache(AHORRO) == Dinero("1000.00")


def test_registrar_asiento_invalido_no_toca_el_ledger() -> None:
    svc, _, ledger = _servicio()
    with pytest.raises(ViolacionSeparacionDeFondos):
        svc.registrar_asiento(_asiento(C.INTERES_PAGADO, AHORRO, Cr), creado_por=1)
    assert ledger.listar() == []


def test_egreso_sin_saldo_lanza_saldo_insuficiente() -> None:
    svc, _, ledger = _servicio()
    with pytest.raises(SaldoInsuficiente):
        svc.registrar_asiento(_asiento(C.DESEMBOLSO_PRESTAMO, AHORRO, D), creado_por=1)
    assert ledger.listar() == []


@pytest.mark.parametrize(
    ("egreso", "esperado_ok"),
    [("999.99", True), ("1000.00", True), ("1000.01", False)],
)
def test_egreso_respeta_el_saldo_disponible(egreso: str, esperado_ok: bool) -> None:
    svc, fondos, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "1000.00"), creado_por=1)
    asiento = _asiento(C.DESEMBOLSO_PRESTAMO, AHORRO, D, monto=egreso)
    if esperado_ok:
        svc.registrar_asiento(asiento, creado_por=1)
        assert fondos.saldo(AHORRO) == Dinero("1000.00") - Dinero(egreso)
    else:
        with pytest.raises(SaldoInsuficiente):
            svc.registrar_asiento(asiento, creado_por=1)


# ---------------------------------------------------------------------------
# Reversión vía servicio (RN-061): espejo, rebalanceo y doble reversión
# ---------------------------------------------------------------------------


def test_reversion_invierte_naturaleza_y_devuelve_el_saldo() -> None:
    svc, fondos, ledger = _servicio()
    leido = svc.registrar_asiento(_mov(Cr, "1000.00", participante_id=7), creado_por=1)
    assert fondos.saldo(AHORRO) == Dinero("1000.00")

    reverso = svc.revertir(leido.uuid, motivo="pago errado", creado_por=1)
    assert reverso.concepto is C.REVERSION
    assert reverso.naturaleza is D  # opuesto al crédito original
    assert reverso.monto == Dinero("1000.00")
    assert fondos.saldo(AHORRO) == Dinero.cero()
    assert svc.saldo_participante(7, AHORRO) == Dinero.cero()
    assert len(ledger.listar()) == 2


def test_reversion_de_un_debito_repone_el_fondo() -> None:
    svc, fondos, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "5000.00"), creado_por=1)
    egreso = svc.registrar_asiento(
        _asiento(C.DESEMBOLSO_PRESTAMO, AHORRO, D, monto="2000.00"), creado_por=1
    )
    assert fondos.saldo(AHORRO) == Dinero("3000.00")
    reverso = svc.revertir(egreso.uuid, motivo="desembolso errado", creado_por=1)
    assert reverso.naturaleza is Cr  # opuesto al débito original
    assert fondos.saldo(AHORRO) == Dinero("5000.00")


def test_revertir_asiento_inexistente_falla() -> None:
    from app.core.errors import NoEncontrado

    svc, _, _ = _servicio()
    with pytest.raises(NoEncontrado):
        svc.revertir("uuid-inexistente", motivo="x", creado_por=1)


def test_doble_reversion_no_esta_bloqueada() -> None:
    # El dominio no impone idempotencia en la reversión (la reversión no valida
    # saldo, doc/servicio): revertir dos veces el MISMO asiento se admite hoy y
    # deja el fondo por debajo de cero. Se documenta el comportamiento actual.
    svc, fondos, ledger = _servicio()
    leido = svc.registrar_asiento(_mov(Cr, "1000.00"), creado_por=1)
    svc.revertir(leido.uuid, motivo="1", creado_por=1)
    svc.revertir(leido.uuid, motivo="2", creado_por=1)  # no lanza
    assert len(ledger.listar()) == 3
    assert fondos.saldo(AHORRO) == Dinero("-1000.00")


# ---------------------------------------------------------------------------
# Reconciliación (RF-802, RN-063): caché vs ledger
# ---------------------------------------------------------------------------


def test_reconciliacion_cuadra_tras_registro_normal() -> None:
    svc, fondos, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "1000.00"), creado_por=1)
    svc.registrar_asiento(_asiento(C.INTERES_PAGADO, RENT, Cr, monto="50.00"), creado_por=1)
    auditoria = AuditoriaFake()
    reporte = ServicioReconciliacion(fondos, auditoria).reconciliar(autor_id=1)
    assert reporte.cuadra is True
    assert all(linea.cuadra for linea in reporte.lineas)
    assert auditoria.registros == []


def test_reconciliacion_detecta_descuadre_y_audita() -> None:
    svc, fondos, _ = _servicio()
    svc.registrar_asiento(_mov(Cr, "1000.00"), creado_por=1)
    # Corromper el caché para forzar un descuadre respecto al ledger.
    fondos.actualizar_cache(AHORRO, Dinero("999.99"))
    auditoria = AuditoriaFake()
    reporte = ServicioReconciliacion(fondos, auditoria).reconciliar(autor_id=42)

    assert reporte.cuadra is False
    ahorro = next(linea for linea in reporte.lineas if linea.fondo is AHORRO)
    assert ahorro.cuadra is False
    assert ahorro.saldo_ledger == Dinero("1000.00")
    assert ahorro.saldo_cache == Dinero("999.99")
    assert len(auditoria.registros) == 1
    autor, accion, entidad, _, detalle = auditoria.registros[0]
    assert (autor, accion, entidad) == (42, "DESCUADRE_DETECTADO", "FONDO")
    assert detalle is not None and "AHORRO" in detalle
