"""Periodicidad end-to-end: sub-períodos por mes, cuota dividida y regeneración."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario
from tests.integration.test_cuotas_flujo import _CONFIG


def _operativa(client: TestClient, session: Session, periodicidad: str) -> tuple[str, dict[str, str]]:
    u = crear_usuario(session)
    nat = crear_natillera(session)  # ciclo 2026-01-01 → 2026-12-31 (12 meses)
    crear_membresia(session, u.id, nat.id)
    session.commit()
    h = bearer(u.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    cfg = {**_CONFIG, "periodicidad_cuota": periodicidad}
    client.put(f"{base}/configuracion", json=cfg, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    return nat.uuid, h


def test_quincenal_genera_dos_por_mes(client: TestClient, session: Session) -> None:
    nat, h = _operativa(client, session, "QUINCENAL")
    periodos = client.get(f"/api/v1/natilleras/{nat}/periodos", headers=h).json()
    assert len(periodos) == 24  # 12 meses × 2
    assert sorted({p["secuencia"] for p in periodos}) == [1, 2]


def test_quincenal_cobra_la_mitad(client: TestClient, session: Session) -> None:
    nat, h = _operativa(client, session, "QUINCENAL")
    base = f"/api/v1/natilleras/{nat}"
    p = client.post(
        f"{base}/participantes",
        json={
            "nombre": "Ana",
            "tipo_documento": "CC",
            "numero_documento": "1010101010",
            "fecha_ingreso": "2026-01-15",
            "valor_cuota": "90000.00",
        },
        headers=h,
    ).json()
    per = client.get(f"{base}/periodos", headers=h).json()[0]["uuid"]
    r = client.post(
        f"{base}/cuotas/pagos",
        json={"participante_uuid": p["uuid"], "periodo_uuid": per},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["monto"] == "45000.00"  # 90.000 mensual ÷ 2 (quincenal)


def test_regenerar_agrega_subperiodos(client: TestClient, session: Session) -> None:
    nat, h = _operativa(client, session, "MENSUAL")
    base = f"/api/v1/natilleras/{nat}"
    assert len(client.get(f"{base}/periodos", headers=h).json()) == 12
    client.put(
        f"{base}/configuracion",
        json={**_CONFIG, "periodicidad_cuota": "QUINCENAL"},
        headers=h,
    )
    r = client.post(f"{base}/periodos/regenerar", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["periodos_creados"] == 12  # agrega la 2ª quincena de cada mes
    assert len(client.get(f"{base}/periodos", headers=h).json()) == 24
