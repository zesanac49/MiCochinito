"""Flujo de actividades/polla end-to-end (RF-501..507, INV-05..09)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario

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
}


def _part(session: Session, base: str, h: dict[str, str], client: TestClient, doc: str) -> str:
    return client.post(
        f"{base}/participantes",
        json={"nombre": f"P{doc}", "tipo_documento": "CC", "numero_documento": doc,
              "fecha_ingreso": "2026-01-15"},
        headers=h,
    ).json()["uuid"]


def _setup(client: TestClient, session: Session) -> tuple[str, str, list[str], dict[str, str]]:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    client.put(f"{base}/configuracion", json=_CONFIG, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    periodo = client.get(f"{base}/periodos", headers=h).json()[0]["uuid"]
    parts = [_part(session, base, h, client, d) for d in ("1110001", "2220002", "3330003")]
    return nat.uuid, periodo, parts, h


def _crear_polla(
    client: TestClient, base: str, h: dict[str, str], periodo: str, premio: str = "10000.00"
) -> str:
    return client.post(
        f"{base}/actividades",
        json={
            "tipo": "POLLA",
            "nombre": "Polla de enero",
            "periodo_uuid": periodo,
            "valor_numero": "10000.00",
            "cantidad_numeros": 5,
            "premio": premio,
        },
        headers=h,
    ).json()["uuid"]


def _asignar_abrir_pagar(
    client: TestClient, a: str, h: dict[str, str], parts: list[str], pagados: list[int]
) -> None:
    client.put(
        f"{a}/numeros",
        json={"asignaciones": [
            {"numero": i + 1, "participante_uuid": parts[i]} for i in range(len(parts))
        ]},
        headers=h,
    )
    client.post(f"{a}/apertura", headers=h)
    client.post(f"{a}/numeros/pagos", json={"numeros": pagados}, headers=h)


def test_polla_con_ganador_utilidad_a_rentabilidad(client: TestClient, session: Session) -> None:
    nat_uuid, periodo, parts, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    act = _crear_polla(client, base, h, periodo, premio="10000.00")
    a = f"{base}/actividades/{act}"
    _asignar_abrir_pagar(client, a, h, parts, [1, 2, 3])  # 30.000 en ingresos

    sorteo = client.post(
        f"{a}/sorteo", json={"numero_ganador": 1, "fuente": "Lotería"}, headers=h
    ).json()
    assert sorteo["sorteo"]["hubo_ganador"] is True
    # Utilidad = 30.000 - 10.000 premio = 20.000 → crédito a Rentabilidad.
    cerrada = client.post(f"{a}/cierre", headers=h).json()
    assert cerrada["estado"] == "CERRADA"
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["RENTABILIDAD"] == "20000.00"


def test_cierre_con_perdida_sin_saldo_bloqueado(client: TestClient, session: Session) -> None:
    nat_uuid, periodo, parts, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    act = _crear_polla(client, base, h, periodo, premio="30000.00")
    a = f"{base}/actividades/{act}"
    _asignar_abrir_pagar(client, a, h, parts, [1])  # 10.000 en ingresos
    client.post(f"{a}/sorteo", json={"numero_ganador": 1, "fuente": "Lotería"}, headers=h)
    # Utilidad = 10.000 - 30.000 premio = -20.000; Rentabilidad sin saldo → bloquea.
    r = client.post(f"{a}/cierre", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "ACTIVIDAD_NO_CERRABLE"


def test_polla_sin_ganador_utilidad_integra(client: TestClient, session: Session) -> None:
    nat_uuid, periodo, parts, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    act = _crear_polla(client, base, h, periodo)
    a = f"{base}/actividades/{act}"
    client.put(
        f"{a}/numeros",
        json={"asignaciones": [{"numero": 1, "participante_uuid": parts[0]}]},
        headers=h,
    )
    client.post(f"{a}/apertura", headers=h)
    client.post(f"{a}/numeros/pagos", json={"numeros": [1]}, headers=h)  # ingreso 10.000
    # Sortea el 4 (no asignado/pagado): sin ganador, sin premio.
    sorteo = client.post(
        f"{a}/sorteo", json={"numero_ganador": 4, "fuente": "Lotería"}, headers=h
    ).json()
    assert sorteo["sorteo"]["hubo_ganador"] is False
    # Utilidad = 10.000 íntegra a Rentabilidad (INV-09).
    cerrada = client.post(f"{a}/cierre", headers=h).json()
    assert cerrada["estado"] == "CERRADA"
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["RENTABILIDAD"] == "10000.00"


def test_clonacion_excluye_pagos_y_sorteo(client: TestClient, session: Session) -> None:
    nat_uuid, periodo, parts, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    act = _crear_polla(client, base, h, periodo)
    a = f"{base}/actividades/{act}"
    client.put(
        f"{a}/numeros",
        json={"asignaciones": [{"numero": 1, "participante_uuid": parts[0]}]},
        headers=h,
    )
    client.post(f"{a}/apertura", headers=h)
    client.post(f"{a}/numeros/pagos", json={"numeros": [1]}, headers=h)

    clon = client.post(
        f"{a}/clonacion", json={"periodo_destino_uuid": periodo}, headers=h
    ).json()
    assert clon["estado"] == "BORRADOR"
    assert len(clon["numeros"]) == 1
    assert clon["numeros"][0]["pagado"] is False  # INV-08: no copia pagos
    assert clon["sorteo"] is None
    assert clon["movimientos"] == []
