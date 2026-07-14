"""RBAC y resolución del principal autenticado (doc 05 §6, RF-1001/1002).

- `Rol`: ADMINISTRADOR | SUPERVISOR | CLIENTE (doc 04 §3.2). El rol vive en la
  membresía usuario-natillera: un usuario puede ser ADM de una natillera y CLI
  de otra, por eso el rol es siempre relativo al tenant activo.
- `Principal`: identidad autenticada más su rol en el tenant de la ruta.
- `require_rol(*roles)`: dependencia de FastAPI que autoriza por rol.

En Sprint 0 la dependencia `obtener_principal_actual` valida el access token y
delega la resolución de membresía (usuario + rol en el tenant) a un puerto
`ResolverPrincipal`, cuya implementación contra la BD llega en Sprint 1
(S1-T06). Esto permite tener y testear el mecanismo de RBAC desde ya.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.deps import obtener_session, obtener_settings
from app.core.errors import NoAutenticado, Prohibido, TokenExpirado
from app.core.security import ErrorDeToken, TipoToken, decodificar_token


class Rol(str, Enum):
    ADMINISTRADOR = "ADMINISTRADOR"
    SUPERVISOR = "SUPERVISOR"
    CLIENTE = "CLIENTE"


@dataclass(frozen=True, slots=True)
class Principal:
    """Identidad autenticada resuelta para el tenant activo."""

    usuario_uuid: str
    usuario_id: int | None = None
    natillera_uuid: str | None = None
    natillera_id: int | None = None
    rol: Rol | None = None
    participante_uuid: str | None = None  # solo CLIENTE (RF-203)


class ResolverPrincipal(Protocol):
    """Puerto: a partir del usuario del token y el tenant de la ruta, resuelve
    la membresía (usuario_id, rol, participante vinculado)."""

    def resolver(self, usuario_uuid: str, natillera_uuid: str | None) -> Principal: ...


# Fábrica de resolver: función que, dada una sesión, devuelve un ResolverPrincipal.
FabricaResolver = Callable[[Session], ResolverPrincipal]


_BEARER = "bearer "


def extraer_access_token(request: Request) -> str:
    encabezado = request.headers.get("Authorization", "")
    if not encabezado.lower().startswith(_BEARER):
        raise NoAutenticado("Falta el encabezado Authorization con Bearer token.")
    return encabezado[len(_BEARER) :].strip()


def usuario_uuid_de_token(settings: Settings, token: str) -> str:
    """Valida un access token y devuelve el usuario (sub). Sin BD."""
    try:
        claims = decodificar_token(settings, token, TipoToken.ACCESS)
    except ErrorDeToken as exc:
        if exc.expirado:
            raise TokenExpirado(exc.mensaje) from exc
        raise NoAutenticado(exc.mensaje) from exc
    sujeto = claims.get("sub")
    if not isinstance(sujeto, str) or not sujeto:
        raise NoAutenticado("Token sin sujeto válido.")
    return sujeto


def require_rol(*roles: Rol) -> Callable[[Principal], Awaitable[Principal]]:
    """Dependencia que exige que el principal tenga uno de los roles dados."""
    permitidos = set(roles)

    async def _dep(principal: Principal = Depends(obtener_principal_actual)) -> Principal:
        if principal.rol is None or principal.rol not in permitidos:
            raise Prohibido(
                "No tienes permiso para esta operación.",
                {"rol_requerido": [r.value for r in permitidos]},
            )
        return principal

    return _dep


async def obtener_principal_actual(
    request: Request,
    settings: Settings = Depends(obtener_settings),
    session: Session = Depends(obtener_session),
) -> Principal:
    """Valida el access token y resuelve el principal (usuario + membresía).

    La resolución de membresía usa la fábrica de resolver de `app.state`
    (conectada en `crear_app`). Sin fábrica configurada, devuelve un principal
    solo con el usuario del token (sin rol); `require_rol` lo rechazará.
    """
    token = extraer_access_token(request)
    usuario_uuid = usuario_uuid_de_token(settings, token)
    natillera_uuid = request.path_params.get("natillera_uuid")
    fabrica: FabricaResolver | None = getattr(request.app.state, "fabrica_resolver", None)
    if fabrica is None:
        return Principal(usuario_uuid=usuario_uuid, natillera_uuid=natillera_uuid)
    return fabrica(session).resolver(usuario_uuid, natillera_uuid)
