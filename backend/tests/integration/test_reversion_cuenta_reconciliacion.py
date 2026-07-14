"""Reversión, estado de cuenta y reconciliación (S2-T06/07/08, RF-305/203/802)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
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
_PART = {
    "nombre": "Ana",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}


def _operativa(client: TestClient, session: Session) -> tuple[str, str, dict[str, str]]:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    client.put(f"{base}/configuracion", json=_CONFIG, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    return nat.uuid, usuario.uuid, h


def _pagar_una_cuota(client: TestClient, nat_uuid: str, h: dict[str, str]) -> tuple[str, dict]:
    base = f"/api/v1/natilleras/{nat_uuid}"
    p = client.post(f"{base}/participantes", json=_PART, headers=h).json()
    periodos = client.get(f"{base}/periodos", headers=h).json()
    asiento = client.post(
        f"{base}/cuotas/pagos",
        json={"participante_uuid": p["uuid"], "periodo_uuid": periodos[0]["uuid"]},
        headers=h,
    ).json()
    return p["uuid"], asiento


def test_reversion_rebalancea_el_fondo(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _operativa(client, session)
    _, asiento = _pagar_una_cuota(client, nat_uuid, h)
    base = f"/api/v1/natilleras/{nat_uuid}"

    r = client.post(
        f"{base}/asientos/{asiento['uuid']}/reversion",
        json={"motivo": "pago registrado por error"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["concepto"] == "REVERSION"
    assert r.json()["naturaleza"] == "DEBITO"  # opuesto al crédito original

    # El saldo del Ahorro vuelve a cero; hay 2 asientos.
    fondos = client.get(f"{base}/fondos", headers=h).json()
    ahorro = next(f for f in fondos if f["tipo"] == "AHORRO")
    assert ahorro["saldo"] == "0.00"
    asientos = client.get(f"{base}/asientos", headers=h).json()
    assert len(asientos) == 2


def test_estado_de_cuenta(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _operativa(client, session)
    part_uuid, _ = _pagar_una_cuota(client, nat_uuid, h)
    r = client.get(
        f"/api/v1/natilleras/{nat_uuid}/participantes/{part_uuid}/cuenta", headers=h
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["saldos"]["ahorros"] == "50000.00"
    assert len(cuerpo["asientos"]) == 1
    assert cuerpo["asientos"][0]["concepto"] == "CUOTA_AHORRO"


def test_reconciliacion_cuadra(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _operativa(client, session)
    _pagar_una_cuota(client, nat_uuid, h)
    r = client.post(f"/api/v1/natilleras/{nat_uuid}/reconciliacion", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["cuadra"] is True


def test_reconciliacion_detecta_descuadre(client: TestClient, session: Session) -> None:
    nat_uuid, _, h = _operativa(client, session)
    _pagar_una_cuota(client, nat_uuid, h)
    # Corrompemos el caché de saldo del Ahorro directamente en la BD.
    fondo = session.scalar(select(FondoModel).where(FondoModel.tipo == "AHORRO"))
    assert fondo is not None
    fondo.saldo_cache = fondo.saldo_cache + 1
    session.commit()

    r = client.post(f"/api/v1/natilleras/{nat_uuid}/reconciliacion", headers=h)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["cuadra"] is False
    ahorro = next(linea for linea in cuerpo["lineas"] if linea["fondo"] == "AHORRO")
    assert ahorro["cuadra"] is False


def test_cliente_no_ve_cuenta_ajena(client: TestClient, session: Session) -> None:
    nat_uuid, _, h_admin = _operativa(client, session)
    part_uuid, _ = _pagar_una_cuota(client, nat_uuid, h_admin)
    # Un usuario CLIENTE sin vínculo a ese participante.
    session.expire_all()
    cliente = crear_usuario(session, email="cli@x.co")
    from app.modules.natilleras.infrastructure.modelos import NatilleraModel

    nat = session.scalar(select(NatilleraModel).where(NatilleraModel.uuid == nat_uuid))
    assert nat is not None
    crear_membresia(session, cliente.id, nat.id, rol="CLIENTE")
    session.commit()
    r = client.get(
        f"/api/v1/natilleras/{nat_uuid}/participantes/{part_uuid}/cuenta",
        headers=bearer(cliente.uuid),
    )
    assert r.status_code == 403
