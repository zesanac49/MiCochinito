"""Tests del servicio de autenticación: rotación y revocación (S0-T07)."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.servicio_auth import (
    AlmacenRefreshTokensEnMemoria,
    ErrorAutenticacion,
    ServicioAutenticacion,
)

SETTINGS = Settings(jwt_secret="secreto-de-prueba-suficientemente-largo-1234567890")


def _servicio() -> ServicioAutenticacion:
    return ServicioAutenticacion(SETTINGS, AlmacenRefreshTokensEnMemoria())


def test_login_emite_par() -> None:
    par = _servicio().emitir_par("u1")
    assert par.access and par.refresh
    assert par.access != par.refresh


def test_refresh_rota_e_invalida_el_anterior() -> None:
    svc = _servicio()
    par1 = svc.emitir_par("u1")
    par2 = svc.refrescar(par1.refresh)

    # El refresh viejo ya no sirve (rotación).
    assert par2.refresh != par1.refresh
    with pytest.raises(ErrorAutenticacion):
        svc.refrescar(par1.refresh)
    # El nuevo sí sirve.
    par3 = svc.refrescar(par2.refresh)
    assert par3.access


def test_logout_revoca_el_refresh() -> None:
    svc = _servicio()
    par = svc.emitir_par("u1")
    svc.logout(par.refresh)
    with pytest.raises(ErrorAutenticacion):
        svc.refrescar(par.refresh)


def test_refresh_desconocido_es_rechazado() -> None:
    svc = _servicio()
    # Un refresh válido en firma pero emitido por otro servicio (jti no registrado).
    otro = _servicio()
    par = otro.emitir_par("u1")
    with pytest.raises(ErrorAutenticacion):
        svc.refrescar(par.refresh)
