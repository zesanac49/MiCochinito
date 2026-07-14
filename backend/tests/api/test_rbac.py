"""RBAC por tenant sobre endpoints reales (S0-T07 + S1-T06, doc 05 §6)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario
from tests.integration.test_cuotas_flujo import _CONFIG


def test_sin_token_devuelve_401(client: TestClient, session: Session) -> None:
    nat = crear_natillera(session)
    session.commit()
    resp = client.post(f"/api/v1/natilleras/{nat.uuid}/transiciones", json={"a": "ABIERTA"})
    assert resp.status_code == 401
    assert resp.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_token_valido_sin_membresia_es_prohibido(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    session.commit()  # usuario existe pero sin membresía en esa natillera
    resp = client.post(
        f"/api/v1/natilleras/{nat.uuid}/transiciones",
        json={"a": "ABIERTA"},
        headers=bearer(usuario.uuid),
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["codigo"] == "PROHIBIDO"


def test_supervisor_puede_transicionar(client: TestClient, session: Session) -> None:
    # El supervisor gestiona la natillera: configurar y avanzar estados (menos liquidar).
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="SUPERVISOR")
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    assert client.put(f"{base}/configuracion", json=_CONFIG, headers=h).status_code == 200
    resp = client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    assert resp.status_code == 200


def test_admin_miembro_puede_leer(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="ADMINISTRADOR")
    session.commit()
    resp = client.get(f"/api/v1/natilleras/{nat.uuid}", headers=bearer(usuario.uuid))
    assert resp.status_code == 200
    assert resp.json()["uuid"] == nat.uuid
