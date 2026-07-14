"""Flujo de participantes end-to-end (RF-201/202) + unicidad y tenancy."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario

_PART = {
    "nombre": "Ana Pérez",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
    "telefono": "3001234567",
}


def _admin(session: Session) -> tuple[str, str]:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="ADMINISTRADOR")
    session.commit()
    return nat.uuid, usuario.uuid


def test_inscribir_y_listar(client: TestClient, session: Session) -> None:
    nat_uuid, usr_uuid = _admin(session)
    h = bearer(usr_uuid)
    r = client.post(f"/api/v1/natilleras/{nat_uuid}/participantes", json=_PART, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "ACTIVO"
    lista = client.get(f"/api/v1/natilleras/{nat_uuid}/participantes", headers=h).json()
    assert len(lista) == 1


def test_documento_duplicado(client: TestClient, session: Session) -> None:
    nat_uuid, usr_uuid = _admin(session)
    h = bearer(usr_uuid)
    client.post(f"/api/v1/natilleras/{nat_uuid}/participantes", json=_PART, headers=h)
    r = client.post(f"/api/v1/natilleras/{nat_uuid}/participantes", json=_PART, headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "VALIDACION"


def test_cambiar_estado(client: TestClient, session: Session) -> None:
    nat_uuid, usr_uuid = _admin(session)
    h = bearer(usr_uuid)
    p = client.post(
        f"/api/v1/natilleras/{nat_uuid}/participantes", json=_PART, headers=h
    ).json()
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/participantes/{p['uuid']}/estado",
        json={"estado": "SUSPENDIDO"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "SUSPENDIDO"


def test_supervisor_no_puede_inscribir(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="SUPERVISOR")
    session.commit()
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/participantes",
        json=_PART,
        headers=bearer(usuario.uuid),
    )
    assert r.status_code == 403
