"""Aislamiento multi-tenant del repositorio base (S0-T05, TEC-02, RNF-02).

Usa SQLite en memoria (permitido para tests de tenancy sin aritmética
monetaria, doc 05 §9). Verifica que un repositorio ligado a una natillera
jamás devuelve datos de otra.
"""

from __future__ import annotations

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.shared.infrastructure.db import ModeloBase, ModeloTenant
from app.shared.infrastructure.repositorio_base import RepositorioBaseConTenant


class _CosaModel(ModeloTenant):
    __tablename__ = "cosas_demo"
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)


class _RepoCosas(RepositorioBaseConTenant[_CosaModel]):
    modelo = _CosaModel


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    ModeloBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return factory()


def test_listar_solo_devuelve_del_tenant(session: Session) -> None:
    repo1 = _RepoCosas(session, natillera_id=1)
    repo2 = _RepoCosas(session, natillera_id=2)
    repo1.agregar(_CosaModel(nombre="de-la-1"))
    repo2.agregar(_CosaModel(nombre="de-la-2"))
    session.flush()

    assert [c.nombre for c in repo1.listar()] == ["de-la-1"]
    assert [c.nombre for c in repo2.listar()] == ["de-la-2"]


def test_agregar_fuerza_el_tenant_del_contexto(session: Session) -> None:
    repo1 = _RepoCosas(session, natillera_id=1)
    # Intento colar la cosa como de la natillera 999; el repo debe forzar la 1.
    cosa = _CosaModel(nombre="intruso", natillera_id=999)
    repo1.agregar(cosa)
    session.flush()
    assert cosa.natillera_id == 1


def test_obtener_por_uuid_respeta_tenant(session: Session) -> None:
    repo1 = _RepoCosas(session, natillera_id=1)
    repo2 = _RepoCosas(session, natillera_id=2)
    cosa = repo1.agregar(_CosaModel(nombre="secreta"))
    session.flush()

    assert repo1.obtener_por_uuid(cosa.uuid) is not None
    assert repo2.obtener_por_uuid(cosa.uuid) is None  # cruza tenant => nada
