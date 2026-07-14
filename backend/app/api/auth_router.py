"""Router de autenticación (RF-1001, doc 07 §2).

Login/refresh/logout gestionan la sesión de BD (escriben refresh tokens) y
hacen commit explícito. La lógica de tokens vive en `ServicioAutenticacion`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas_auth import (
    LoginRequest,
    MembresiaResponse,
    MeResponse,
    RefreshRequest,
    TokenResponse,
)
from app.core.auth import Principal, obtener_principal_actual
from app.core.config import Settings
from app.core.deps import obtener_session, obtener_settings
from app.core.errors import NoAutenticado
from app.core.security import verificar_password
from app.core.servicio_auth import ErrorAutenticacion, ServicioAutenticacion
from app.modules.natilleras.infrastructure.modelos import NatilleraModel
from app.shared.infrastructure.almacen_refresh import AlmacenRefreshTokensSQLAlchemy
from app.shared.infrastructure.modelos_auth import UsuarioNatilleraModel
from app.shared.infrastructure.repositorio_usuarios import RepositorioUsuarios

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _servicio(session: Session, settings: Settings) -> ServicioAutenticacion:
    return ServicioAutenticacion(
        settings, AlmacenRefreshTokensSQLAlchemy(session, settings)
    )


@router.post("/login", response_model=TokenResponse)
def login(
    datos: LoginRequest,
    session: Session = Depends(obtener_session),
    settings: Settings = Depends(obtener_settings),
) -> TokenResponse:
    usuario = RepositorioUsuarios(session).obtener_por_email(datos.email)
    if usuario is None or not usuario.activo:
        raise NoAutenticado("Credenciales inválidas.")
    if not verificar_password(datos.password, usuario.hash_password):
        raise NoAutenticado("Credenciales inválidas.")
    par = _servicio(session, settings).emitir_par(usuario.uuid)
    session.commit()
    return TokenResponse(access_token=par.access, refresh_token=par.refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    datos: RefreshRequest,
    session: Session = Depends(obtener_session),
    settings: Settings = Depends(obtener_settings),
) -> TokenResponse:
    try:
        par = _servicio(session, settings).refrescar(datos.refresh_token)
    except ErrorAutenticacion as exc:
        session.rollback()
        raise NoAutenticado(exc.mensaje) from exc
    session.commit()
    return TokenResponse(access_token=par.access, refresh_token=par.refresh)


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    datos: RefreshRequest,
    session: Session = Depends(obtener_session),
    settings: Settings = Depends(obtener_settings),
) -> Response:
    _servicio(session, settings).logout(datos.refresh_token)
    session.commit()
    return Response(status_code=204)


@router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(obtener_principal_actual),
    session: Session = Depends(obtener_session),
) -> MeResponse:
    usuario = RepositorioUsuarios(session).obtener_por_uuid(principal.usuario_uuid)
    if usuario is None:
        raise NoAutenticado("Usuario inexistente.")
    filas = session.execute(
        select(UsuarioNatilleraModel.rol, NatilleraModel.uuid, NatilleraModel.nombre)
        .join(NatilleraModel, UsuarioNatilleraModel.natillera_id == NatilleraModel.id)
        .where(UsuarioNatilleraModel.usuario_id == usuario.id)
    ).all()
    return MeResponse(
        uuid=usuario.uuid,
        email=usuario.email,
        nombre=usuario.nombre,
        membresias=[
            MembresiaResponse(natillera_uuid=nat_uuid, natillera_nombre=nombre, rol=rol)
            for rol, nat_uuid, nombre in filas
        ],
    )
