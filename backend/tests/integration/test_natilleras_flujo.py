"""Flujo de natilleras end-to-end (RF-101/102/103) + aislamiento de tenant (RNF-02)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.contabilidad.infrastructure.modelos import FondoModel
from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario

_CONFIG = {
    "valor_cuota": "50000.00",
    "periodicidad_cuota": "MENSUAL",
    "dia_limite_pago": 5,
    "permite_aportes_extra": True,
    "tasa_interes_base": "2.0",
    "tasa_interes_min": "1.0",
    "tasa_interes_max": "3.0",
    "max_prestamos_activos": 2,
    "max_capital_vigente": "2000000.00",
    "estrategia_distribucion": "PROPORCIONAL_AHORRO",
}


def test_crear_natillera_crea_dos_fondos(
    client: TestClient, session: Session
) -> None:
    usuario = crear_usuario(session)
    session.commit()
    resp = client.post(
        "/api/v1/natilleras",
        json={
            "nombre": "Nueva",
            "ciclo_inicio": "2026-01-01",
            "ciclo_fin": "2026-12-31",
            "configuracion": _CONFIG,
        },
        headers=bearer(usuario.uuid),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["estado"] == "BORRADOR"
    # RN-001: exactamente dos fondos.
    total = session.scalar(select(func.count()).select_from(FondoModel))
    assert total == 2


def test_transicion_borrador_a_abierta_requiere_config(
    client: TestClient, session: Session
) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)  # sin configuración
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    resp = client.post(
        f"/api/v1/natilleras/{nat.uuid}/transiciones",
        json={"a": "ABIERTA"},
        headers=bearer(usuario.uuid),
    )
    assert resp.status_code == 409  # TRANSICION_INVALIDA (sin config)


def test_configurar_y_transicionar(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    r_cfg = client.put(
        f"/api/v1/natilleras/{nat.uuid}/configuracion", json=_CONFIG, headers=h
    )
    assert r_cfg.status_code == 200
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/transiciones", json={"a": "ABIERTA"}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "ABIERTA"


def test_salto_de_estado_invalido(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/transiciones",
        json={"a": "LIQUIDADA"},
        headers=bearer(usuario.uuid),
    )
    assert r.status_code == 409


def test_aislamiento_de_tenant(client: TestClient, session: Session) -> None:
    """RNF-02: un usuario de la natillera A no puede ver la natillera B."""
    usuario_a = crear_usuario(session, email="a@x.co")
    nat_a = crear_natillera(session, "A")
    nat_b = crear_natillera(session, "B")
    crear_membresia(session, usuario_a.id, nat_a.id)  # solo en A
    session.commit()
    h = bearer(usuario_a.uuid)
    assert client.get(f"/api/v1/natilleras/{nat_a.uuid}", headers=h).status_code == 200
    assert client.get(f"/api/v1/natilleras/{nat_b.uuid}", headers=h).status_code == 403
    # El listado solo trae las suyas.
    lista = client.get("/api/v1/natilleras", headers=h).json()
    assert [n["nombre"] for n in lista] == ["A"]
