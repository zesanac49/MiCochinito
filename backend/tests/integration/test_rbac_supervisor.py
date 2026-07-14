"""RBAC del supervisor: gestiona casi toda la natillera, menos crearla/liquidarla.

El supervisor puede configurar, avanzar estados, préstamos, multas y actividades;
NO puede iniciar/confirmar la liquidación (solo el administrador).
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario
from tests.integration.test_cuotas_flujo import _CONFIG

_PART = {
    "nombre": "Ana",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}


def _supervisor(session: Session) -> tuple[str, dict[str, str]]:
    u = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, u.id, nat.id, rol="SUPERVISOR")
    session.commit()
    return nat.uuid, bearer(u.uuid)


def test_supervisor_gestiona_natillera(client: TestClient, session: Session) -> None:
    nat, h = _supervisor(session)
    base = f"/api/v1/natilleras/{nat}"

    # Configurar y avanzar estados.
    assert client.put(f"{base}/configuracion", json=_CONFIG, headers=h).status_code == 200
    assert client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h).status_code == 200
    assert (
        client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h).status_code
        == 200
    )

    # Multas: crear catálogo e imponer.
    cat = client.post(
        f"{base}/catalogo-multas",
        json={"nombre": "Mora", "tipo": "OTRA", "valor": "10000"},
        headers=h,
    )
    assert cat.status_code == 201, cat.text
    p = client.post(f"{base}/participantes", json=_PART, headers=h).json()
    imp = client.post(
        f"{base}/multas",
        json={
            "participante_uuid": p["uuid"],
            "motivo": "Llegó tarde",
            "catalogo_uuid": cat.json()["uuid"],
        },
        headers=h,
    )
    assert imp.status_code == 201, imp.text

    # Actividades: crear (requiere un período).
    per = client.get(f"{base}/periodos", headers=h).json()[0]["uuid"]
    act = client.post(
        f"{base}/actividades",
        json={
            "tipo": "POLLA",
            "nombre": "Polla de enero",
            "periodo_uuid": per,
            "valor_numero": "5000",
            "cantidad_numeros": 10,
            "premio": "20000",
        },
        headers=h,
    )
    assert act.status_code == 201, act.text


def test_supervisor_no_puede_liquidar(client: TestClient, session: Session) -> None:
    nat, h = _supervisor(session)
    # Iniciar la liquidación es solo del administrador.
    r = client.post(f"/api/v1/natilleras/{nat}/liquidacion", headers=h)
    assert r.status_code == 403, r.text
