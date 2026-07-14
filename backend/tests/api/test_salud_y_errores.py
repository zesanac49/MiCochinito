"""Tests de salud, request_id y formato uniforme de error (S0-T03)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import NoEncontrado
from app.main import crear_app
from app.shared.domain.excepciones import TransicionInvalida


def _cliente() -> TestClient:
    app: FastAPI = crear_app(Settings(entorno="test", log_json=False))

    @app.get("/_boom_dominio")
    async def _boom_dominio() -> None:
        raise TransicionInvalida(
            "No se puede pasar de BORRADOR a LIQUIDADA.", {"desde": "BORRADOR"}
        )

    @app.get("/_boom_api")
    async def _boom_api() -> None:
        raise NoEncontrado("Participante inexistente.")

    return TestClient(app, raise_server_exceptions=False)


def test_health_ok() -> None:
    resp = _cliente().get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"estado": "ok"}


def test_request_id_en_header() -> None:
    resp = _cliente().get("/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_se_respeta_si_viene() -> None:
    resp = _cliente().get("/health", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["X-Request-ID"] == "abc-123"


def test_error_de_dominio_formato_uniforme() -> None:
    resp = _cliente().get("/_boom_dominio")
    assert resp.status_code == 409  # TransicionInvalida (doc 07 §4)
    cuerpo = resp.json()
    assert cuerpo["error"]["codigo"] == "TRANSICION_INVALIDA"
    assert cuerpo["error"]["detalle"] == {"desde": "BORRADOR"}
    assert cuerpo["error"]["request_id"]


def test_error_api_no_encontrado() -> None:
    resp = _cliente().get("/_boom_api")
    assert resp.status_code == 404
    assert resp.json()["error"]["codigo"] == "NO_ENCONTRADO"
