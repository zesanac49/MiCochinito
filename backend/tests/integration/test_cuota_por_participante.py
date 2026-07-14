"""Cuota propia por participante (RF-301): monto fijo distinto por persona,
con fallback al valor por defecto de la configuración."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.test_cuotas_flujo import _natillera_operativa

_FECHA = "2026-01-15"


def _inscribir(
    client: TestClient,
    nat: str,
    h: dict[str, str],
    nombre: str,
    doc: str,
    valor_cuota: str | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "nombre": nombre,
        "tipo_documento": "CC",
        "numero_documento": doc,
        "fecha_ingreso": _FECHA,
    }
    if valor_cuota is not None:
        body["valor_cuota"] = valor_cuota
    r = client.post(f"/api/v1/natilleras/{nat}/participantes", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _periodo0(client: TestClient, nat: str, h: dict[str, str]) -> str:
    return str(client.get(f"/api/v1/natilleras/{nat}/periodos", headers=h).json()[0]["uuid"])


def _pagar(client: TestClient, nat: str, h: dict[str, str], part: str, per: str) -> dict:
    return client.post(
        f"/api/v1/natilleras/{nat}/cuotas/pagos",
        json={"participante_uuid": part, "periodo_uuid": per},
        headers=h,
    ).json()


def test_alta_con_cuota_propia(client: TestClient, session: Session) -> None:
    nat, h = _natillera_operativa(client, session)
    ana = _inscribir(client, nat, h, "Ana", "1010101010", valor_cuota="80000.00")
    assert ana["valor_cuota"] == "80000.00"


def test_pago_individual_usa_cuota_propia_o_default(
    client: TestClient, session: Session
) -> None:
    nat, h = _natillera_operativa(client, session)  # config default valor_cuota=50000
    per = _periodo0(client, nat, h)
    ana = _inscribir(client, nat, h, "Ana", "1010101010", valor_cuota="80000.00")
    beto = _inscribir(client, nat, h, "Beto", "2020202020")  # sin cuota propia

    a = _pagar(client, nat, h, str(ana["uuid"]), per)
    b = _pagar(client, nat, h, str(beto["uuid"]), per)
    assert a["monto"] == "80000.00"      # su cuota propia
    assert b["monto"] == "50000.00"      # el default de la config


def test_fijar_cuota_endpoint(client: TestClient, session: Session) -> None:
    nat, h = _natillera_operativa(client, session)
    per = _periodo0(client, nat, h)
    beto = _inscribir(client, nat, h, "Beto", "2020202020")
    r = client.put(
        f"/api/v1/natilleras/{nat}/participantes/{beto['uuid']}/cuota",
        json={"valor_cuota": "120000.00"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["valor_cuota"] == "120000.00"
    # El pago posterior usa la nueva cuota.
    assert _pagar(client, nat, h, str(beto["uuid"]), per)["monto"] == "120000.00"


def test_lote_suma_cuotas_distintas(client: TestClient, session: Session) -> None:
    nat, h = _natillera_operativa(client, session)
    per = _periodo0(client, nat, h)
    ana = _inscribir(client, nat, h, "Ana", "1010101010", valor_cuota="80000.00")
    beto = _inscribir(client, nat, h, "Beto", "2020202020")  # default 50000
    items = [
        {"participante_uuid": ana["uuid"], "periodo_uuid": per},
        {"participante_uuid": beto["uuid"], "periodo_uuid": per},
    ]
    r = client.post(
        f"/api/v1/natilleras/{nat}/cuotas/pagos-lote", json={"items": items}, headers=h
    )
    assert r.status_code == 200, r.text
    resumen = r.json()
    assert resumen["cantidad_pagados"] == 2
    assert resumen["total_recaudado"] == "130000.00"  # 80000 + 50000


def test_cuota_no_positiva_rechazada(client: TestClient, session: Session) -> None:
    nat, h = _natillera_operativa(client, session)
    beto = _inscribir(client, nat, h, "Beto", "2020202020")
    r = client.put(
        f"/api/v1/natilleras/{nat}/participantes/{beto['uuid']}/cuota",
        json={"valor_cuota": "0.00"},
        headers=h,
    )
    assert r.status_code == 409, r.text
