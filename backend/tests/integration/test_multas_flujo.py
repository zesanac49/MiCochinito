"""Flujo de multas end-to-end (RF-601/602/603, INV-10)."""

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


def _setup(client: TestClient, session: Session) -> tuple[str, str, dict[str, str]]:
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
    return nat.uuid, p["uuid"], h


def test_imponer_desde_catalogo_y_pagar(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    cat = client.post(
        f"{base}/catalogo-multas",
        json={"nombre": "Mora en cuota", "tipo": "MORA_CUOTA", "valor": "10000.00"},
        headers=h,
    ).json()

    multa = client.post(
        f"{base}/multas",
        json={
            "participante_uuid": part_uuid,
            "motivo": "no pagó a tiempo",
            "catalogo_uuid": cat["uuid"],
        },
        headers=h,
    ).json()
    assert multa["estado"] == "IMPUESTA"
    assert multa["valor"] == "10000.00"

    # Solo el PAGO genera rentabilidad (INV-10).
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["RENTABILIDAD"] == "0.00"

    pagada = client.post(f"{base}/multas/{multa['uuid']}/pago", headers=h).json()
    assert pagada["estado"] == "PAGADA"
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["RENTABILIDAD"] == "10000.00"


def test_anular_multa_impuesta(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    multa = client.post(
        f"{base}/multas",
        json={"participante_uuid": part_uuid, "motivo": "error", "valor": "5000.00"},
        headers=h,
    ).json()
    r = client.post(
        f"{base}/multas/{multa['uuid']}/anulacion",
        json={"justificacion": "impuesta por error"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADA"


def test_multa_pagada_no_se_anula(client: TestClient, session: Session) -> None:
    nat_uuid, part_uuid, h = _setup(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    multa = client.post(
        f"{base}/multas",
        json={"participante_uuid": part_uuid, "motivo": "x", "valor": "5000.00"},
        headers=h,
    ).json()
    client.post(f"{base}/multas/{multa['uuid']}/pago", headers=h)
    r = client.post(
        f"{base}/multas/{multa['uuid']}/anulacion",
        json={"justificacion": "ya no aplica"},
        headers=h,
    )
    assert r.status_code == 409  # TransicionInvalida
    assert r.json()["error"]["codigo"] == "TRANSICION_INVALIDA"
