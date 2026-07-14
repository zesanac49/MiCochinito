"""Flujo de préstamos end-to-end (RF-401..405, RN-033..038, INV-04)."""

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
_PART = {
    "nombre": "Ana",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}


def _setup(
    client: TestClient, session: Session, ahorro: str = "5000000.00"
) -> tuple[str, str, dict[str, str]]:
    """Natillera EN_OPERACION con un participante y el Fondo de Ahorro fondeado
    mediante un aporte extraordinario. Devuelve (nat_uuid, participante_uuid, headers)."""
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    client.put(f"{base}/configuracion", json=_CONFIG, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    p = client.post(f"{base}/participantes", json=_PART, headers=h).json()
    client.post(
        f"{base}/aportes-extraordinarios",
        json={"participante_uuid": p["uuid"], "monto": ahorro},
        headers=h,
    )
    return nat.uuid, p["uuid"], h


def _solicitar(client, base, h, part_uuid, capital="1000000.00", tasa="2.0"):  # type: ignore[no-untyped-def]
    return client.post(
        f"{base}/prestamos",
        json={"participante_uuid": part_uuid, "capital": capital, "tasa": tasa, "plazo_meses": 12},
        headers=h,
    )


def test_ciclo_completo_de_prestamo(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"

    pr = _solicitar(client, base, h, part_uuid).json()
    assert pr["estado"] == "SOLICITADO"

    assert client.post(
        f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h
    ).json()["estado"] == "APROBADO"

    des = client.post(f"{base}/prestamos/{pr['uuid']}/desembolso", headers=h).json()
    assert des["estado"] == "EN_PAGO"
    assert des["saldo_capital"] == "1000000.00"
    # El Ahorro bajó (5.000.000 - 1.000.000).
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["AHORRO"] == "4000000.00"

    # Pago: interés del período = 1.000.000 × 2% = 20.000; capital = 100.000.
    pago = client.post(
        f"{base}/prestamos/{pr['uuid']}/pagos", json={"monto": "120000.00"}, headers=h
    ).json()
    assert pago["descomposicion"] == {
        "capital": "100000.00", "interes": "20000.00", "total": "120000.00",
    }
    assert len(pago["asientos"]) == 2
    assert pago["prestamo"]["saldo_capital"] == "900000.00"
    # 2 asientos: capital a Ahorro, interés a Rentabilidad.
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["AHORRO"] == "4100000.00"
    assert fondos["RENTABILIDAD"] == "20000.00"


def test_pago_total_marca_pagado(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    pr = _solicitar(client, base, h, part_uuid).json()
    client.post(f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h)
    client.post(f"{base}/prestamos/{pr['uuid']}/desembolso", headers=h)
    # Adeudado = 1.000.000 + 20.000.
    fin = client.post(
        f"{base}/prestamos/{pr['uuid']}/pagos", json={"monto": "1020000.00"}, headers=h
    ).json()
    assert fin["prestamo"]["estado"] == "PAGADO"
    assert fin["prestamo"]["saldo_capital"] == "0.00"


def test_saldo_insuficiente_bloquea_aprobacion(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session, ahorro="500000.00")  # menos que el capital
    base = f"/api/v1/natilleras/{nat_uuid}"
    pr = _solicitar(client, base, h, part_uuid).json()
    r = client.post(
        f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "SALDO_INSUFICIENTE"


def test_tope_capital_excedido(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    # Capital 3.000.000 > max_capital_vigente 2.000.000.
    pr = _solicitar(client, base, h, part_uuid, capital="3000000.00").json()
    r = client.post(
        f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "TOPE_CAPITAL_EXCEDIDO"


def test_tope_prestamos_concurrentes(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    # Aprueba 2 préstamos de 500.000 (bajo el tope de capital) → activos = 2.
    for _ in range(2):
        pr = _solicitar(client, base, h, part_uuid, capital="500000.00").json()
        client.post(f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h)
    # El tercero excede el tope de préstamos concurrentes (2).
    pr3 = _solicitar(client, base, h, part_uuid, capital="500000.00").json()
    r = client.post(
        f"{base}/prestamos/{pr3['uuid']}/aprobacion", json={"aprobar": True}, headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "TOPE_PRESTAMOS_EXCEDIDO"


def test_rechazo_de_solicitud(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    pr = _solicitar(client, base, h, part_uuid).json()
    r = client.post(
        f"{base}/prestamos/{pr['uuid']}/aprobacion",
        json={"aprobar": False, "motivo": "sin capacidad"},
        headers=h,
    )
    assert r.json()["estado"] == "RECHAZADO"
    assert r.json()["motivo_rechazo"] == "sin capacidad"
