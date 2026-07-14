"""Primitivas de seguridad: hashing de contraseñas y JWT (RF-1001, doc 05 §6).

- Contraseñas: passlib + bcrypt.
- Tokens: PyJWT. Access (15 min) y refresh (14 días) con `jti` para permitir
  rotación (cada refresh emite un jti nuevo) y revocación (el jti se marca
  revocado en el almacén de refresh tokens, tabla del doc 04 §3.2).

El reloj se inyecta (`ahora`) para poder testear expiraciones sin esperar.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import Settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

Reloj = Callable[[], datetime]


def _ahora_utc() -> datetime:
    return datetime.now(UTC)


class TipoToken(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class ErrorDeToken(Exception):
    """Token inválido, expirado o del tipo incorrecto (lo mapea la capa api)."""

    def __init__(self, mensaje: str, expirado: bool = False) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.expirado = expirado


# --- Contraseñas -----------------------------------------------------------


def hashear_password(password: str) -> str:
    return str(_pwd.hash(password))


def verificar_password(password: str, hash_almacenado: str) -> bool:
    return bool(_pwd.verify(password, hash_almacenado))


# --- Tokens ----------------------------------------------------------------


def _crear_token(
    settings: Settings,
    sujeto: str,
    tipo: TipoToken,
    expira_en: timedelta,
    ahora: Reloj,
    jti: str | None = None,
) -> str:
    emitido = ahora()
    claims: dict[str, Any] = {
        "sub": sujeto,
        "tipo": tipo.value,
        "iat": int(emitido.timestamp()),
        "exp": int((emitido + expira_en).timestamp()),
    }
    if jti is not None:
        claims["jti"] = jti
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algoritmo)


def crear_access_token(
    settings: Settings, usuario_uuid: str, ahora: Reloj = _ahora_utc
) -> str:
    return _crear_token(
        settings,
        usuario_uuid,
        TipoToken.ACCESS,
        timedelta(minutes=settings.access_token_minutos),
        ahora,
    )


def crear_refresh_token(
    settings: Settings,
    usuario_uuid: str,
    ahora: Reloj = _ahora_utc,
    jti: str | None = None,
) -> tuple[str, str]:
    """Devuelve (token, jti). El jti identifica el refresh para rotación/revocación."""
    jti = jti or str(uuid.uuid4())
    token = _crear_token(
        settings,
        usuario_uuid,
        TipoToken.REFRESH,
        timedelta(days=settings.refresh_token_dias),
        ahora,
        jti=jti,
    )
    return token, jti


def decodificar_token(
    settings: Settings, token: str, tipo_esperado: TipoToken
) -> dict[str, Any]:
    """Valida firma, expiración y tipo. Lanza `ErrorDeToken` si algo falla."""
    try:
        claims: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo]
        )
    except jwt.ExpiredSignatureError as exc:
        raise ErrorDeToken("El token ha expirado.", expirado=True) from exc
    except jwt.InvalidTokenError as exc:
        raise ErrorDeToken("Token inválido.") from exc
    if claims.get("tipo") != tipo_esperado.value:
        raise ErrorDeToken(
            f"Se esperaba un token de tipo {tipo_esperado.value}."
        )
    return claims
