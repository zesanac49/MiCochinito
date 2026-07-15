"""Casos borde de liquidación (RN-072..074, RN-073, INV-14).

Dos bloques:

* Estrategias de distribución como **unit** (property/parametrizado): la suma de
  participaciones cuadra EXACTAMENTE con el fondo en `Decimal`, el residuo va al
  de mayor participación, y los repartos degenerados (ahorros en 0) reparten en
  partes iguales.
* Flujo de liquidación por **API** (fixtures de `conftest`): fórmula del saldo
  final (capital, intereses, multas y mora de cuotas), confirmación por nombre,
  bloqueos y máquina de fases.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.actividades.infrastructure.modelos import ActividadModel
from app.modules.contabilidad.infrastructure.modelos import PeriodoModel
from app.modules.liquidacion.domain.estrategias import (
    ParticipanteLiquidable,
    crear_estrategia,
)
from app.modules.prestamos.infrastructure.modelos import PrestamoModel
from app.shared.domain.dinero import Dinero
from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario

# ===========================================================================
# BLOQUE 1 — ESTRATEGIAS (unit)
# ===========================================================================

_ESTRATEGIAS = ["PARTES_IGUALES", "PROPORCIONAL_AHORRO", "PROPORCIONAL_TIEMPO"]


def _liq(pid: int, ahorro: str, meses: int = 12) -> ParticipanteLiquidable:
    return ParticipanteLiquidable(pid, Dinero(ahorro), meses)


def _participantes(datos: list[tuple[str, int]]) -> list[ParticipanteLiquidable]:
    return [_liq(i, a, m) for i, (a, m) in enumerate(datos, start=1)]


# Fondos variados: cero, impares/con residuo, pequeños y grandes.
_FONDOS = [
    "0.00",
    "0.01",
    "0.03",
    "1.00",
    "7.00",
    "33.33",
    "100.00",
    "100.01",
    "50000.01",
    "99999999.99",
]

# Configuraciones de participantes: 1 solo, iguales, desiguales, ahorros en 0,
# y muchos.
_CONFIGS: list[list[tuple[str, int]]] = [
    [("0", 12)],
    [("100000", 12)],
    [("0", 12), ("0", 12), ("0", 12)],
    [("100", 12), ("100", 12)],
    [("100", 1), ("200", 24), ("300", 60)],
    [("1", 12), ("1", 12), ("5", 12)],
    [(str(i * 111), i + 1) for i in range(15)],
]


@pytest.mark.parametrize("estrategia", _ESTRATEGIAS)
@pytest.mark.parametrize("fondo", _FONDOS)
@pytest.mark.parametrize("config", _CONFIGS)
def test_suma_participaciones_igual_al_fondo_exacto(
    estrategia: str, fondo: str, config: list[tuple[str, int]]
) -> None:
    """RN-073: Σ participaciones == fondo, exacto en Decimal, sin negativos."""
    est = crear_estrategia(estrategia)
    partes = est.distribuir(Dinero(fondo), _participantes(config))
    total = sum((p.monto for p in partes.values()), Decimal(0))
    assert total == Dinero(fondo).monto
    assert all(not p.es_negativo() for p in partes.values())
    assert len(partes) == len(config)


@pytest.mark.parametrize("estrategia", _ESTRATEGIAS)
@pytest.mark.parametrize("fondo", ["0.00", "0.01", "12345.67", "99999999.99"])
def test_un_solo_participante_recibe_todo(estrategia: str, fondo: str) -> None:
    est = crear_estrategia(estrategia)
    partes = est.distribuir(Dinero(fondo), [_liq(1, "50000")])
    assert partes == {1: Dinero(fondo)}


@pytest.mark.parametrize("estrategia", _ESTRATEGIAS)
def test_lista_vacia_retorna_vacio(estrategia: str) -> None:
    est = crear_estrategia(estrategia)
    assert est.distribuir(Dinero("100.00"), []) == {}


@pytest.mark.parametrize("estrategia", ["PROPORCIONAL_AHORRO", "PROPORCIONAL_TIEMPO"])
def test_ahorros_en_cero_reparte_en_partes_iguales(estrategia: str) -> None:
    """Pesos degenerados (todos los ahorros en 0) => reparto en partes iguales."""
    est = crear_estrategia(estrategia)
    partes = est.distribuir(
        Dinero("90000.00"), _participantes([("0", 12), ("0", 12), ("0", 12)])
    )
    assert partes == {1: Dinero("30000.00"), 2: Dinero("30000.00"), 3: Dinero("30000.00")}
    total = sum((p.monto for p in partes.values()), Decimal(0))
    assert total == Decimal("90000.00")


def test_residuo_al_de_mayor_participacion_proporcional() -> None:
    """El residuo por redondeo va al de mayor ahorro (mayor participación)."""
    est = crear_estrategia("PROPORCIONAL_AHORRO")
    # Ahorros 1,1,5 sobre un fondo de 0.03: el de ahorro 5 se lleva todo (0.03).
    partes = est.distribuir(Dinero("0.03"), _participantes([("1", 12), ("1", 12), ("5", 12)]))
    assert partes[1] == Dinero("0.00")
    assert partes[2] == Dinero("0.00")
    assert partes[3] == Dinero("0.03")
    assert sum((p.monto for p in partes.values()), Decimal(0)) == Decimal("0.03")


def test_residuo_partes_iguales_va_a_un_solo_participante() -> None:
    est = crear_estrategia("PARTES_IGUALES")
    # 100 / 3 = 33.33 c/u (99.99); el residuo 0.01 recae en uno solo.
    partes = est.distribuir(Dinero("100.00"), _participantes([("0", 1), ("0", 1), ("0", 1)]))
    montos = sorted(p.monto for p in partes.values())
    assert montos == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(montos) == Decimal("100.00")


def test_ponderada_por_tiempo_pondera_ahorro_y_meses() -> None:
    est = crear_estrategia("PROPORCIONAL_TIEMPO")
    # Pesos: 100*1=100 y 100*3=300 => 25% y 75% de 40.000.
    partes = est.distribuir(Dinero("40000.00"), [_liq(1, "100", 1), _liq(2, "100", 3)])
    assert partes[1] == Dinero("10000.00")
    assert partes[2] == Dinero("30000.00")


# ===========================================================================
# BLOQUE 2 — FLUJO POR API (integration)
# ===========================================================================

_CONFIG = {
    "valor_cuota": "50000.00",
    "periodicidad_cuota": "MENSUAL",
    "dia_limite_pago": 5,
    "permite_aportes_extra": True,
    "tasa_interes_base": "2.0",
    "tasa_interes_min": "1.0",
    "tasa_interes_max": "3.0",
    "max_prestamos_activos": 2,
    "max_capital_vigente": "2000000.00",
    "estrategia_distribucion": "PROPORCIONAL_AHORRO",
    "valor_mora": "0",
}


def _part(client: TestClient, base: str, h: dict[str, str], nombre: str, doc: str) -> str:
    return client.post(
        f"{base}/participantes",
        json={"nombre": nombre, "tipo_documento": "CC", "numero_documento": doc,
              "fecha_ingreso": "2026-01-15"},
        headers=h,
    ).json()["uuid"]


def _preparar(
    client: TestClient,
    session: Session,
    *,
    valor_mora: str = "0",
    con_rentabilidad: bool = True,
) -> tuple[int, str, str, dict[str, str], list[str]]:
    """Natillera EN_OPERACION con ahorro y (opcional) rentabilidad de una multa
    pagada. Devuelve (natillera_id, uuid, nombre, headers, [p1, p2])."""
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    cfg = dict(_CONFIG, valor_mora=valor_mora)
    client.put(f"{base}/configuracion", json=cfg, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    p1 = _part(client, base, h, "Ana", "1110001")
    p2 = _part(client, base, h, "Beto", "2220002")
    aporte = f"{base}/aportes-extraordinarios"
    client.post(aporte, json={"participante_uuid": p1, "monto": "100000.00"}, headers=h)
    client.post(aporte, json={"participante_uuid": p2, "monto": "300000.00"}, headers=h)
    if con_rentabilidad:
        client.post(
            f"{base}/catalogo-multas",
            json={"nombre": "Mora", "tipo": "OTRA", "valor": "40000.00"},
            headers=h,
        )
        m = client.post(
            f"{base}/multas",
            json={"participante_uuid": p1, "motivo": "pagada", "valor": "40000.00"},
            headers=h,
        ).json()
        client.post(f"{base}/multas/{m['uuid']}/pago", headers=h)
    return nat.id, nat.uuid, nat.nombre, h, [p1, p2]


def _prestamo_desembolsado(
    client: TestClient, base: str, h: dict[str, str], participante_uuid: str, capital: str
) -> str:
    pr = client.post(
        f"{base}/prestamos",
        json={"participante_uuid": participante_uuid, "capital": capital,
              "tasa": "2.0", "plazo_meses": 6},
        headers=h,
    ).json()
    client.post(f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h)
    client.post(f"{base}/prestamos/{pr['uuid']}/desembolso", headers=h)
    return pr["uuid"]


def _forzar_una_mora(session: Session, natillera_id: int, dias_atraso: int) -> None:
    """Neutraliza los períodos autogenerados del ciclo y deja UNO vencido, para
    una mora determinista de `valor_mora * (dias_atraso // 7)`."""
    periodos = list(
        session.scalars(
            select(PeriodoModel).where(PeriodoModel.natillera_id == natillera_id)
        ).all()
    )
    assert periodos, "el ciclo debería tener períodos autogenerados"
    for p in periodos:
        p.fecha_limite_cuota = None
    periodos[0].fecha_limite_cuota = date.today() - timedelta(days=dias_atraso)
    session.commit()


def _un_periodo_id(session: Session, natillera_id: int) -> int:
    pid = session.scalar(
        select(PeriodoModel.id).where(PeriodoModel.natillera_id == natillera_id)
    )
    assert pid is not None
    return pid


def _resolver_bloqueos(client: TestClient, base: str, h: dict[str, str]) -> None:
    ini = client.post(f"{base}/liquidacion", headers=h).json()
    for b in ini["bloqueos"]:
        client.post(
            f"{base}/liquidacion/decisiones",
            json={"tipo_bloqueo": b["tipo"], "origen_tipo": b["origen_tipo"],
                  "origen_id": b["origen_id"], "decision": "IGNORAR"},
            headers=h,
        )


# --- Fórmula del saldo final -----------------------------------------------


def test_saldo_final_resta_capital_intereses_multas_y_mora(
    client: TestClient, session: Session
) -> None:
    """saldo_final = ahorros + rentabilidad − capital − intereses − multas
    (multas impuestas + mora de cuotas vencidas)."""
    nid, nat_uuid, nombre, h, (p1, _p2) = _preparar(
        client, session, valor_mora="1000.00"
    )
    base = f"/api/v1/natilleras/{nat_uuid}"

    # Préstamo activo de p1: capital vigente + interés devengado real.
    pr_uuid = _prestamo_desembolsado(client, base, h, p1, "100000.00")
    prestamo = session.scalar(select(PrestamoModel).where(PrestamoModel.uuid == pr_uuid))
    assert prestamo is not None
    prestamo.estado = "EN_PAGO"
    prestamo.interes_acumulado = Decimal("5000.00")
    prestamo.fecha_ultimo_calculo = date.today()

    # Multa IMPUESTA (no pagada) => pendiente de p1.
    client.post(
        f"{base}/catalogo-multas",
        json={"nombre": "Sancion", "tipo": "OTRA", "valor": "40000.00"},
        headers=h,
    )
    client.post(
        f"{base}/multas",
        json={"participante_uuid": p1, "motivo": "impuesta", "valor": "40000.00"},
        headers=h,
    )

    # Un único período vencido y no pagado => mora = valor_mora * semanas.
    p1_id = prestamo.participante_id
    session.commit()  # persiste la mutación del préstamo antes de tocar períodos
    _forzar_una_mora(session, nid, dias_atraso=21)  # 21 // 7 = 3 semanas

    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    _resolver_bloqueos(client, base, h)

    calc = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert calc.status_code == 200, calc.text
    detalle = next(
        d for d in calc.json()["detalles"] if d["participante_uuid"] == p1
    )

    assert detalle["capital_pendiente"] == "100000.00"
    assert detalle["intereses_pendientes"] == "5000.00"
    # Multa impuesta 40.000 + mora (1.000 * 3 semanas) = 43.000.
    assert detalle["multas_pendientes"] == "43000.00"

    esperado = (
        Dinero(detalle["ahorros"])
        + Dinero(detalle["participacion_rentabilidad"])
        - Dinero(detalle["capital_pendiente"])
        - Dinero(detalle["intereses_pendientes"])
        - Dinero(detalle["multas_pendientes"])
    )
    assert detalle["saldo_final"] == esperado.como_str()
    assert p1_id  # sanity: el participante existía


def test_mora_cero_no_suma_a_multas(client: TestClient, session: Session) -> None:
    """Con valor_mora=0 no hay mora aunque existan períodos vencidos (el ciclo ya
    trae períodos autogenerados con fecha límite pasada)."""
    _nid, nat_uuid, _, h, (p1, _p2) = _preparar(client, session, valor_mora="0")
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)
    calc = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert calc.status_code == 200, calc.text
    detalle = next(d for d in calc.json()["detalles"] if d["participante_uuid"] == p1)
    assert detalle["multas_pendientes"] == "0.00"


# --- Confirmación por nombre ------------------------------------------------


def test_confirmacion_nombre_exacto_confirma(client: TestClient, session: Session) -> None:
    _nid, nat_uuid, nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)
    client.post(f"{base}/liquidacion/calculo", headers=h)
    ok = client.post(
        f"{base}/liquidacion/confirmacion", json={"nombre_natillera": nombre}, headers=h
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["fase"] == "CONFIRMADA"
    assert client.get(base, headers=h).json()["estado"] == "LIQUIDADA"


@pytest.mark.parametrize("nombre_malo", ["otro", "", "  ", "los ahorradores"])
def test_confirmacion_nombre_incorrecto_409(
    client: TestClient, session: Session, nombre_malo: str
) -> None:
    _nid, nat_uuid, _nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)
    client.post(f"{base}/liquidacion/calculo", headers=h)
    r = client.post(
        f"{base}/liquidacion/confirmacion", json={"nombre_natillera": nombre_malo}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "CONFIRMACION_INCORRECTA"


def test_confirmacion_ignora_espacios_alrededor(client: TestClient, session: Session) -> None:
    """`confirmar` compara con `.strip()`: espacios envolventes no invalidan."""
    _nid, nat_uuid, nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)
    client.post(f"{base}/liquidacion/calculo", headers=h)
    r = client.post(
        f"{base}/liquidacion/confirmacion",
        json={"nombre_natillera": f"  {nombre}  "}, headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["fase"] == "CONFIRMADA"


# --- Bloqueos ---------------------------------------------------------------


@pytest.mark.parametrize("estado", ["DESEMBOLSADO", "EN_PAGO", "EN_MORA"])
def test_bloqueo_por_prestamo_activo(
    client: TestClient, session: Session, estado: str
) -> None:
    _nid, nat_uuid, _nombre, h, (p1, _p2) = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    pr_uuid = _prestamo_desembolsado(client, base, h, p1, "100000.00")
    if estado != "DESEMBOLSADO":
        pr = session.scalar(select(PrestamoModel).where(PrestamoModel.uuid == pr_uuid))
        assert pr is not None
        pr.estado = estado
        session.commit()
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)

    ini = client.post(f"{base}/liquidacion", headers=h).json()
    assert any(b["tipo"] == "PRESTAMO_NO_PAGADO" for b in ini["bloqueos"])
    r = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "LIQUIDACION_BLOQUEADA"


def test_bloqueo_por_actividad_abierta(client: TestClient, session: Session) -> None:
    nid, nat_uuid, _nombre, h, _ = _preparar(client, session, con_rentabilidad=False)
    base = f"/api/v1/natilleras/{nat_uuid}"
    session.add(
        ActividadModel(
            natillera_id=nid, tipo="OTRO", nombre="Bazar",
            periodo_id=_un_periodo_id(session, nid), estado="ABIERTA",
        )
    )
    session.commit()
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)

    ini = client.post(f"{base}/liquidacion", headers=h).json()
    assert any(b["tipo"] == "ACTIVIDAD_ABIERTA" for b in ini["bloqueos"])
    r = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "LIQUIDACION_BLOQUEADA"


def test_sin_bloqueos_procede_a_calcular(client: TestClient, session: Session) -> None:
    _nid, nat_uuid, _nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    ini = client.post(f"{base}/liquidacion", headers=h).json()
    assert ini["bloqueos"] == []
    calc = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert calc.status_code == 200, calc.text
    assert calc.json()["fase"] == "CALCULADA"


# --- Máquina de fases -------------------------------------------------------


def test_ciclo_completo_hasta_liquidada(client: TestClient, session: Session) -> None:
    _nid, nat_uuid, nombre, h, (p1, p2) = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    assert client.post(f"{base}/liquidacion", headers=h).json()["bloqueos"] == []
    calc = client.post(f"{base}/liquidacion/calculo", headers=h).json()
    assert calc["fase"] == "CALCULADA"
    por_uuid = {d["participante_uuid"]: d for d in calc["detalles"]}
    # Rentabilidad 40.000 proporcional al ahorro (25%/75%).
    assert por_uuid[p1]["participacion_rentabilidad"] == "10000.00"
    assert por_uuid[p2]["participacion_rentabilidad"] == "30000.00"
    ok = client.post(
        f"{base}/liquidacion/confirmacion", json={"nombre_natillera": nombre}, headers=h
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["fase"] == "CONFIRMADA"
    assert client.get(base, headers=h).json()["estado"] == "LIQUIDADA"


def test_confirmar_sin_calcular_falla(client: TestClient, session: Session) -> None:
    _nid, nat_uuid, nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)  # inicia pero NO calcula
    r = client.post(
        f"{base}/liquidacion/confirmacion", json={"nombre_natillera": nombre}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "TRANSICION_INVALIDA"


def test_doble_confirmacion_falla(client: TestClient, session: Session) -> None:
    _nid, nat_uuid, nombre, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)
    client.post(f"{base}/liquidacion", headers=h)
    client.post(f"{base}/liquidacion/calculo", headers=h)
    conf = f"{base}/liquidacion/confirmacion"
    primera = client.post(conf, json={"nombre_natillera": nombre}, headers=h)
    assert primera.status_code == 200, primera.text
    # La natillera ya está LIQUIDADA: LIQUIDAR deja de estar permitido.
    segunda = client.post(conf, json={"nombre_natillera": nombre}, headers=h)
    assert segunda.status_code == 409
    assert segunda.json()["error"]["codigo"] == "OPERACION_NO_PERMITIDA_EN_ESTADO"


def test_cero_participantes_activos_calcula_vacio(
    client: TestClient, session: Session
) -> None:
    """Natillera sin participantes activos: la liquidación calcula sin detalles."""
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    client.put(f"{base}/configuracion", json=_CONFIG, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)

    assert client.post(f"{base}/liquidacion", headers=h).json()["bloqueos"] == []
    calc = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert calc.status_code == 200, calc.text
    cuerpo = calc.json()
    assert cuerpo["fase"] == "CALCULADA"
    assert cuerpo["detalles"] == []
