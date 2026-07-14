"""Fixtures compartidos: app FastAPI sobre SQLite en memoria con tablas creadas.

Usa StaticPool para que la BD `:memory:` sea la MISMA a través de todas las
sesiones (setup del test + requests de la app comparten conexión). Permitido
para tests de API/tenancy sin aritmética monetaria pesada (doc 05 §9); los tests
financieros exactos contra MySQL van marcados `@pytest.mark.mysql`.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.shared.infrastructure.todos_los_modelos  # noqa: F401  (puebla metadata)
from app.core.config import Settings
from app.core.security import crear_access_token, hashear_password
from app.main import crear_app
from app.modules.contabilidad.infrastructure.modelos import FondoModel
from app.modules.natilleras.infrastructure.modelos import NatilleraModel
from app.shared.infrastructure.db import ModeloBase
from app.shared.infrastructure.modelos_auth import (
    UsuarioModel,
    UsuarioNatilleraModel,
)

SETTINGS = Settings(
    entorno="test",
    log_json=False,
    jwt_secret="secreto-de-prueba-suficientemente-largo-1234567890",
)


@pytest.fixture()
def engine() -> Engine:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ModeloBase.metadata.create_all(eng)
    return eng


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def app(engine: Engine, session_factory: sessionmaker[Session]) -> FastAPI:
    aplicacion = crear_app(SETTINGS)
    aplicacion.state.engine = engine
    aplicacion.state.session_factory = session_factory
    return aplicacion


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


# --- Helpers de siembra ----------------------------------------------------


def crear_usuario(
    session: Session, email: str = "admin@natillera.co", password: str = "clave123"
) -> UsuarioModel:
    u = UsuarioModel(
        email=email, hash_password=hashear_password(password), nombre="Admin", activo=True
    )
    session.add(u)
    session.flush()
    return u


def crear_natillera(session: Session, nombre: str = "Los Ahorradores") -> NatilleraModel:
    n = NatilleraModel(
        nombre=nombre,
        estado="BORRADOR",
        ciclo_inicio=date(2026, 1, 1),
        ciclo_fin=date(2026, 12, 31),
    )
    session.add(n)
    session.flush()
    # Toda natillera tiene sus dos fondos (RN-001), como los crea CrearNatillera.
    for tipo in ("AHORRO", "RENTABILIDAD"):
        session.add(FondoModel(natillera_id=n.id, tipo=tipo, saldo_cache=0))
    session.flush()
    return n


def crear_membresia(
    session: Session, usuario_id: int, natillera_id: int, rol: str = "ADMINISTRADOR"
) -> UsuarioNatilleraModel:
    m = UsuarioNatilleraModel(usuario_id=usuario_id, natillera_id=natillera_id, rol=rol)
    session.add(m)
    session.flush()
    return m


def bearer(usuario_uuid: str) -> dict[str, str]:
    token = crear_access_token(SETTINGS, usuario_uuid)
    return {"Authorization": f"Bearer {token}"}
