"""Tests de primitivas de seguridad: hashing y JWT (S0-T07, RF-1001)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.security import (
    ErrorDeToken,
    TipoToken,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
    hashear_password,
    verificar_password,
)

SETTINGS = Settings(jwt_secret="secreto-de-prueba-suficientemente-largo-1234567890")


def test_hash_y_verificacion_de_password() -> None:
    h = hashear_password("clave-super-secreta")
    assert h != "clave-super-secreta"
    assert verificar_password("clave-super-secreta", h)
    assert not verificar_password("otra", h)


def test_access_token_ida_y_vuelta() -> None:
    token = crear_access_token(SETTINGS, "usuario-uuid-1")
    claims = decodificar_token(SETTINGS, token, TipoToken.ACCESS)
    assert claims["sub"] == "usuario-uuid-1"
    assert claims["tipo"] == "access"


def test_refresh_token_lleva_jti() -> None:
    token, jti = crear_refresh_token(SETTINGS, "usuario-uuid-1")
    claims = decodificar_token(SETTINGS, token, TipoToken.REFRESH)
    assert claims["jti"] == jti


def test_token_de_tipo_incorrecto_es_rechazado() -> None:
    access = crear_access_token(SETTINGS, "u1")
    with pytest.raises(ErrorDeToken):
        decodificar_token(SETTINGS, access, TipoToken.REFRESH)


def test_token_expirado() -> None:
    ayer = lambda: datetime.now(UTC) - timedelta(days=1)  # noqa: E731
    token = crear_access_token(SETTINGS, "u1", ahora=ayer)
    with pytest.raises(ErrorDeToken) as info:
        decodificar_token(SETTINGS, token, TipoToken.ACCESS)
    assert info.value.expirado


def test_firma_invalida() -> None:
    token = crear_access_token(SETTINGS, "u1")
    otro = Settings(jwt_secret="otro-secreto-completamente-distinto-0987654321")
    with pytest.raises(ErrorDeToken):
        decodificar_token(otro, token, TipoToken.ACCESS)
