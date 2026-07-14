"""Generación de períodos al abrir la natillera (S2-T02, end-to-end)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def test_abrir_genera_periodos(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)  # ciclo 2026-01-01 .. 2026-12-31
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)

    # Sin abrir aún: no hay períodos.
    assert client.get(f"/api/v1/natilleras/{nat.uuid}/periodos", headers=h).json() == []

    client.put(f"/api/v1/natilleras/{nat.uuid}/configuracion", json=_CONFIG, headers=h)
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/transiciones", json={"a": "ABIERTA"}, headers=h
    )
    assert r.status_code == 200

    periodos = client.get(f"/api/v1/natilleras/{nat.uuid}/periodos", headers=h).json()
    assert len(periodos) == 12
    assert periodos[0]["anio"] == 2026 and periodos[0]["mes"] == 1
