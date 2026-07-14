"""Flujo de gestión de usuarios y accesos end-to-end (RF-1002).

SQLite en memoria (sin aritmética monetaria). Cubre: alta de miembro nuevo y
vinculación de uno existente, regla CLIENTE↔participante, duplicados, protección
del último administrador, RBAC (solo admin gestiona) y reinicio de clave.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario

_PART = {
    "nombre": "Ana Pérez",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}


def _admin(session: Session) -> tuple[str, str, dict[str, str]]:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="ADMINISTRADOR")
    session.commit()
    return nat.uuid, usuario.uuid, bearer(usuario.uuid)


def _crear_participante(client: TestClient, nat_uuid: str, h: dict[str, str]) -> str:
    r = client.post(f"/api/v1/natilleras/{nat_uuid}/participantes", json=_PART, headers=h)
    assert r.status_code == 201, r.text
    return str(r.json()["uuid"])


def test_agregar_miembro_nuevo_y_login(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Sofía Ruiz",
            "email": "sofia@natillera.co",
            "password": "clave12345",
            "rol": "SUPERVISOR",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["creado"] is True

    lista = client.get(f"/api/v1/natilleras/{nat_uuid}/miembros", headers=h).json()
    assert len(lista) == 2
    roles = {m["email"]: m["rol"] for m in lista}
    assert roles["sofia@natillera.co"] == "SUPERVISOR"

    # La contraseña temporal permite ingresar.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "sofia@natillera.co", "password": "clave12345"},
    )
    assert login.status_code == 200, login.text


def test_agregar_usuario_existente_se_vincula(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    # Usuario ya existe globalmente (p.ej. es miembro de otra natillera).
    crear_usuario(session, email="otro@natillera.co", password="suclave123")
    session.commit()

    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Ignorado",
            "email": "otro@natillera.co",
            "password": "no-se-usa-1234",
            "rol": "SUPERVISOR",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["creado"] is False
    # No se cambió su contraseña original.
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "otro@natillera.co", "password": "suclave123"},
    )
    assert login.status_code == 200, login.text


def test_cliente_requiere_participante(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Cliente Sin Part",
            "email": "cli@natillera.co",
            "password": "clave12345",
            "rol": "CLIENTE",
        },
        headers=h,
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["codigo"] == "CLIENTE_REQUIERE_PARTICIPANTE"


def test_cliente_con_participante_ok(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    part_uuid = _crear_participante(client, nat_uuid, h)
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Ana Cliente",
            "email": "ana@natillera.co",
            "password": "clave12345",
            "rol": "CLIENTE",
            "participante_uuid": part_uuid,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    lista = client.get(f"/api/v1/natilleras/{nat_uuid}/miembros", headers=h).json()
    cliente = next(m for m in lista if m["email"] == "ana@natillera.co")
    assert cliente["participante_uuid"] == part_uuid
    assert cliente["participante_nombre"] == "Ana Pérez"


def test_miembro_duplicado(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    cuerpo = {
        "nombre": "Repetida",
        "email": "rep@natillera.co",
        "password": "clave12345",
        "rol": "SUPERVISOR",
    }
    assert client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros", json=cuerpo, headers=h
    ).status_code == 201
    r = client.post(f"/api/v1/natilleras/{nat_uuid}/miembros", json=cuerpo, headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "MIEMBRO_YA_EXISTE"


def test_no_degradar_ultimo_admin(client: TestClient, session: Session) -> None:
    nat_uuid, admin_uuid, h = _admin(session)
    r = client.patch(
        f"/api/v1/natilleras/{nat_uuid}/miembros/{admin_uuid}",
        json={"rol": "SUPERVISOR"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "ULTIMO_ADMINISTRADOR"


def test_degradar_admin_con_otro_admin(client: TestClient, session: Session) -> None:
    nat_uuid, admin_uuid, h = _admin(session)
    # Se agrega un segundo administrador.
    otro = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Otro Admin",
            "email": "admin2@natillera.co",
            "password": "clave12345",
            "rol": "ADMINISTRADOR",
        },
        headers=h,
    ).json()["usuario_uuid"]
    assert otro
    # Ahora sí se puede degradar al primero.
    r = client.patch(
        f"/api/v1/natilleras/{nat_uuid}/miembros/{admin_uuid}",
        json={"rol": "SUPERVISOR"},
        headers=h,
    )
    assert r.status_code == 204, r.text


def test_no_quitar_ultimo_admin(client: TestClient, session: Session) -> None:
    nat_uuid, admin_uuid, h = _admin(session)
    r = client.delete(
        f"/api/v1/natilleras/{nat_uuid}/miembros/{admin_uuid}", headers=h
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "ULTIMO_ADMINISTRADOR"


def test_supervisor_no_puede_gestionar(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="SUPERVISOR")
    session.commit()
    h = bearer(usuario.uuid)
    # Puede listar (admin+supervisor)...
    assert client.get(f"/api/v1/natilleras/{nat.uuid}/miembros", headers=h).status_code == 200
    # ...pero no agregar (solo admin).
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/miembros",
        json={
            "nombre": "X",
            "email": "x@natillera.co",
            "password": "clave12345",
            "rol": "CLIENTE",
        },
        headers=h,
    )
    assert r.status_code == 403


def test_reiniciar_clave(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _admin(session)
    usuario_uuid = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros",
        json={
            "nombre": "Con Clave",
            "email": "clave@natillera.co",
            "password": "clavevieja1",
            "rol": "SUPERVISOR",
        },
        headers=h,
    ).json()["usuario_uuid"]

    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/miembros/{usuario_uuid}/clave",
        json={"password": "clavenueva9"},
        headers=h,
    )
    assert r.status_code == 204, r.text
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "clave@natillera.co", "password": "clavenueva9"},
    ).status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "clave@natillera.co", "password": "clavevieja1"},
    ).status_code == 401
