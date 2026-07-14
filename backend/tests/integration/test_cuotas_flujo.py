"""Flujo de cuotas, idempotencia, lote y aportes (RF-301/302/303, S2-T03/04/05)."""

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

_PART = {
    "nombre": "Ana",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}


def _llevar_a_operacion(
    client: TestClient, nat_uuid: str, h: dict[str, str], cfg: dict[str, object] = _CONFIG
) -> None:
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.put(f"{base}/configuracion", json=cfg, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)


def _natillera_operativa(client: TestClient, session: Session) -> tuple[str, dict[str, str]]:
    """Crea natillera con config, la lleva a EN_OPERACION. Devuelve (uuid, headers)."""
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    _llevar_a_operacion(client, nat.uuid, h)
    return nat.uuid, h


def _participante_y_periodo(
    client: TestClient, nat_uuid: str, h: dict[str, str]
) -> tuple[str, str]:
    base = f"/api/v1/natilleras/{nat_uuid}"
    p = client.post(f"{base}/participantes", json=_PART, headers=h).json()
    periodos = client.get(f"{base}/periodos", headers=h).json()
    return p["uuid"], periodos[0]["uuid"]


def test_pago_de_cuota_credita_ahorro(client: TestClient, session: Session) -> None:
    nat_uuid, h = _natillera_operativa(client, session)
    part_uuid, per_uuid = _participante_y_periodo(client, nat_uuid, h)
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/cuotas/pagos",
        json={"participante_uuid": part_uuid, "periodo_uuid": per_uuid},
        headers=h,
    )
    assert r.status_code == 201, r.text
    asiento = r.json()
    assert asiento["concepto"] == "CUOTA_AHORRO"
    assert asiento["fondo"] == "AHORRO"
    assert asiento["monto"] == "50000.00"
    # El saldo del Fondo de Ahorro sube.
    fondos = client.get(f"/api/v1/natilleras/{nat_uuid}/fondos", headers=h).json()
    ahorro = next(f for f in fondos if f["tipo"] == "AHORRO")
    assert ahorro["saldo"] == "50000.00"


def test_doble_pago_del_periodo_es_rechazado(client: TestClient, session: Session) -> None:
    nat_uuid, h = _natillera_operativa(client, session)
    part_uuid, per_uuid = _participante_y_periodo(client, nat_uuid, h)
    cuerpo = {"participante_uuid": part_uuid, "periodo_uuid": per_uuid}
    url = f"/api/v1/natilleras/{nat_uuid}/cuotas/pagos"
    assert client.post(url, json=cuerpo, headers=h).status_code == 201
    r = client.post(url, json=cuerpo, headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "PERIODO_YA_PAGADO"


def test_idempotency_key_reproduce_resultado(client: TestClient, session: Session) -> None:
    nat_uuid, h = _natillera_operativa(client, session)
    part_uuid, per_uuid = _participante_y_periodo(client, nat_uuid, h)
    cuerpo = {"participante_uuid": part_uuid, "periodo_uuid": per_uuid}
    h_idem = {**h, "Idempotency-Key": "clave-1"}
    r1 = client.post(f"/api/v1/natilleras/{nat_uuid}/cuotas/pagos", json=cuerpo, headers=h_idem)
    r2 = client.post(f"/api/v1/natilleras/{nat_uuid}/cuotas/pagos", json=cuerpo, headers=h_idem)
    assert r1.status_code == 201 and r2.status_code == 201
    # Misma clave => mismo asiento (replay, no un segundo pago).
    assert r1.json()["uuid"] == r2.json()["uuid"]


def test_aporte_bloqueado_sin_flag(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    _llevar_a_operacion(client, nat.uuid, h, {**_CONFIG, "permite_aportes_extra": False})
    p = client.post(
        f"/api/v1/natilleras/{nat.uuid}/participantes", json=_PART, headers=h
    ).json()
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/aportes-extraordinarios",
        json={"participante_uuid": p["uuid"], "monto": "100000.00"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "FUNCIONALIDAD_NO_DISPONIBLE"


def test_pago_en_lote_con_resumen(client: TestClient, session: Session) -> None:
    nat_uuid, h = _natillera_operativa(client, session)
    part_uuid, _ = _participante_y_periodo(client, nat_uuid, h)
    periodos = client.get(f"/api/v1/natilleras/{nat_uuid}/periodos", headers=h).json()
    items = [
        {"participante_uuid": part_uuid, "periodo_uuid": periodos[0]["uuid"]},
        {"participante_uuid": part_uuid, "periodo_uuid": periodos[1]["uuid"]},
    ]
    r = client.post(
        f"/api/v1/natilleras/{nat_uuid}/cuotas/pagos-lote", json={"items": items}, headers=h
    )
    assert r.status_code == 200, r.text
    resumen = r.json()
    assert resumen["cantidad_pagados"] == 2
    assert resumen["total_recaudado"] == "100000.00"


def test_movimiento_bloqueado_en_borrador(client: TestClient, session: Session) -> None:
    # Sin abrir (BORRADOR): no se permite MOVIMIENTO_FINANCIERO.
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    p = client.post(f"/api/v1/natilleras/{nat.uuid}/participantes", json=_PART, headers=h).json()
    r = client.post(
        f"/api/v1/natilleras/{nat.uuid}/cuotas/pagos",
        json={"participante_uuid": p["uuid"], "periodo_uuid": "cualquiera"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "OPERACION_NO_PERMITIDA_EN_ESTADO"
