"""Servicio de autenticación: login, refresh con rotación y logout (RF-1001).

Rotación: cada uso de un refresh token emite un par nuevo y REVOCA el jti
anterior, de modo que un refresh token solo sirve una vez. Revocación: el
almacén marca inactivo un jti (logout o rotación). El almacén es un puerto; su
implementación contra la tabla `refresh_tokens` (doc 04 §3.2) llega en Sprint 1.
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings
from app.core.security import (
    ErrorDeToken,
    Reloj,
    TipoToken,
    _ahora_utc,
    crear_access_token,
    crear_refresh_token,
    decodificar_token,
)


class AlmacenRefreshTokens(Protocol):
    """Puerto de persistencia de refresh tokens (revocación por jti)."""

    def registrar(self, jti: str, usuario_uuid: str) -> None: ...

    def esta_activo(self, jti: str) -> bool: ...

    def revocar(self, jti: str) -> None: ...


class AlmacenRefreshTokensEnMemoria:
    """Impl en memoria para tests y arranque local (no persiste)."""

    def __init__(self) -> None:
        self._activos: dict[str, str] = {}

    def registrar(self, jti: str, usuario_uuid: str) -> None:
        self._activos[jti] = usuario_uuid

    def esta_activo(self, jti: str) -> bool:
        return jti in self._activos

    def revocar(self, jti: str) -> None:
        self._activos.pop(jti, None)


class ParDeTokens:
    __slots__ = ("access", "refresh")

    def __init__(self, access: str, refresh: str) -> None:
        self.access = access
        self.refresh = refresh


class ErrorAutenticacion(Exception):
    def __init__(self, mensaje: str, expirado: bool = False) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.expirado = expirado


class ServicioAutenticacion:
    def __init__(
        self,
        settings: Settings,
        almacen: AlmacenRefreshTokens,
        ahora: Reloj = _ahora_utc,
    ) -> None:
        self._settings = settings
        self._almacen = almacen
        self._ahora = ahora

    def emitir_par(self, usuario_uuid: str) -> ParDeTokens:
        """Emite un par nuevo y registra el jti del refresh (usado en login)."""
        access = crear_access_token(self._settings, usuario_uuid, self._ahora)
        refresh, jti = crear_refresh_token(self._settings, usuario_uuid, self._ahora)
        self._almacen.registrar(jti, usuario_uuid)
        return ParDeTokens(access, refresh)

    def refrescar(self, refresh_token: str) -> ParDeTokens:
        """Rota el refresh: valida, revoca el jti usado y emite un par nuevo."""
        claims = self._decodificar_refresh(refresh_token)
        jti = claims.get("jti")
        usuario_uuid = claims.get("sub")
        if not isinstance(jti, str) or not isinstance(usuario_uuid, str):
            raise ErrorAutenticacion("Refresh token malformado.")
        if not self._almacen.esta_activo(jti):
            raise ErrorAutenticacion("Refresh token revocado o ya utilizado.")
        self._almacen.revocar(jti)  # rotación: el token viejo deja de servir
        return self.emitir_par(usuario_uuid)

    def logout(self, refresh_token: str) -> None:
        """Revoca el refresh token (idempotente ante tokens ya inválidos)."""
        try:
            claims = self._decodificar_refresh(refresh_token)
        except ErrorAutenticacion:
            return
        jti = claims.get("jti")
        if isinstance(jti, str):
            self._almacen.revocar(jti)

    def _decodificar_refresh(self, refresh_token: str) -> dict[str, object]:
        try:
            return decodificar_token(self._settings, refresh_token, TipoToken.REFRESH)
        except ErrorDeToken as exc:
            raise ErrorAutenticacion(exc.mensaje, expirado=exc.expirado) from exc
