"""Flujo de autenticación end-to-end (RF-1001, S1)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario


def test_login_devuelve_par_de_tokens(client: TestClient, session: Session) -> None:
    crear_usuario(session, email="a@x.co", password="secreta1")
    session.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "a@x.co", "password": "secreta1"})
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["access_token"] and cuerpo["refresh_token"]
    assert cuerpo["token_type"] == "bearer"


def test_login_password_incorrecta(client: TestClient, session: Session) -> None:
    crear_usuario(session, email="a@x.co", password="secreta1")
    session.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "a@x.co", "password": "mala"})
    assert resp.status_code == 401


def test_refresh_rota_el_token(client: TestClient, session: Session) -> None:
    crear_usuario(session, email="a@x.co", password="secreta1")
    session.commit()
    par = client.post(
        "/api/v1/auth/login", json={"email": "a@x.co", "password": "secreta1"}
    ).json()
    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": par["refresh_token"]})
    assert r1.status_code == 200
    # El refresh viejo ya no sirve (rotación).
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": par["refresh_token"]})
    assert r2.status_code == 401


def test_me_lista_membresias(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="ADMINISTRADOR")
    session.commit()
    resp = client.get("/api/v1/auth/me", headers=bearer(usuario.uuid))
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["email"] == usuario.email
    assert len(cuerpo["membresias"]) == 1
    assert cuerpo["membresias"][0]["rol"] == "ADMINISTRADOR"
