"""Flujo de liquidación end-to-end (RF-701..706, RN-072..074)."""

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


def _part(client: TestClient, base: str, h: dict[str, str], nombre: str, doc: str) -> str:
    return client.post(
        f"{base}/participantes",
        json={"nombre": nombre, "tipo_documento": "CC", "numero_documento": doc,
              "fecha_ingreso": "2026-01-15"},
        headers=h,
    ).json()["uuid"]


def _preparar(client: TestClient, session: Session) -> tuple[str, str, dict[str, str], list[str]]:
    """Natillera EN_OPERACION con ahorro (aportes) y rentabilidad (multa pagada)."""
    usuario = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id)
    session.commit()
    h = bearer(usuario.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    client.put(f"{base}/configuracion", json=_CONFIG, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    p1 = _part(client, base, h, "Ana", "1110001")
    p2 = _part(client, base, h, "Beto", "2220002")
    # Ahorro: aportes 100k y 300k (total 400k).
    aporte = f"{base}/aportes-extraordinarios"
    client.post(aporte, json={"participante_uuid": p1, "monto": "100000.00"}, headers=h)
    client.post(aporte, json={"participante_uuid": p2, "monto": "300000.00"}, headers=h)
    # Rentabilidad: una multa pagada de 40.000.
    client.post(
        f"{base}/catalogo-multas",
        json={"nombre": "Mora", "tipo": "OTRA", "valor": "40000.00"},
        headers=h,
    )
    m = client.post(
        f"{base}/multas",
        json={"participante_uuid": p1, "motivo": "x", "valor": "40000.00"},
        headers=h,
    ).json()
    client.post(f"{base}/multas/{m['uuid']}/pago", headers=h)
    return nat.uuid, nat.nombre, h, [p1, p2]


def test_ciclo_de_liquidacion_completo(client: TestClient, session: Session) -> None:
    nat_uuid, nombre, h, (p1, p2) = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)

    # Iniciar (sin bloqueos).
    ini = client.post(f"{base}/liquidacion", headers=h).json()
    assert ini["bloqueos"] == []

    # Calcular: rentabilidad 40.000 proporcional al ahorro (25%/75%) → 10.000/30.000.
    calc = client.post(f"{base}/liquidacion/calculo", headers=h).json()
    assert calc["fase"] == "CALCULADA"
    por_uuid = {d["participante_uuid"]: d for d in calc["detalles"]}
    assert por_uuid[p1]["ahorros"] == "100000.00"
    assert por_uuid[p1]["participacion_rentabilidad"] == "10000.00"
    assert por_uuid[p1]["saldo_final"] == "110000.00"
    assert por_uuid[p2]["participacion_rentabilidad"] == "30000.00"

    conf = f"{base}/liquidacion/confirmacion"
    # Confirmar con nombre incorrecto → rechazado.
    mal = client.post(conf, json={"nombre_natillera": "otro"}, headers=h)
    assert mal.status_code == 409
    assert mal.json()["error"]["codigo"] == "CONFIRMACION_INCORRECTA"

    # Confirmar con nombre correcto → asientos de cierre + natillera LIQUIDADA.
    ok = client.post(conf, json={"nombre_natillera": nombre}, headers=h).json()
    assert ok["fase"] == "CONFIRMADA"
    assert client.get(f"{base}", headers=h).json()["estado"] == "LIQUIDADA"
    # Ambos fondos quedan en cero.
    fondos = {f["tipo"]: f["saldo"] for f in client.get(f"{base}/fondos", headers=h).json()}
    assert fondos["AHORRO"] == "0.00"
    assert fondos["RENTABILIDAD"] == "0.00"

    # Registrar entrega a un participante.
    ent = client.post(f"{base}/liquidacion/entregas", json={"participante_uuid": p1}, headers=h)
    assert ent.status_code == 204


def test_bloqueo_por_prestamo_activo(client: TestClient, session: Session) -> None:
    nat_uuid, _, h, (p1, _p2) = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    # Un préstamo desembolsado (activo) usando el ahorro disponible.
    pr = client.post(
        f"{base}/prestamos",
        json={"participante_uuid": p1, "capital": "100000.00", "tasa": "2.0", "plazo_meses": 6},
        headers=h,
    ).json()
    client.post(f"{base}/prestamos/{pr['uuid']}/aprobacion", json={"aprobar": True}, headers=h)
    client.post(f"{base}/prestamos/{pr['uuid']}/desembolso", headers=h)
    client.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"}, headers=h)

    ini = client.post(f"{base}/liquidacion", headers=h).json()
    assert len(ini["bloqueos"]) >= 1
    # Calcular con bloqueos → LIQUIDACION_BLOQUEADA.
    r = client.post(f"{base}/liquidacion/calculo", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "LIQUIDACION_BLOQUEADA"


def test_dashboard_rentabilidad_por_fuente(client: TestClient, session: Session) -> None:
    nat_uuid, _, h, _ = _preparar(client, session)
    base = f"/api/v1/natilleras/{nat_uuid}"
    dash = client.get(f"{base}/dashboard", headers=h).json()
    assert dash["rentabilidad_por_fuente"]["MULTA_PAGADA"] == "40000.00"
    ahorro = next(f for f in dash["fondos"] if f["tipo"] == "AHORRO")
    assert ahorro["saldo"] == "400000.00"
