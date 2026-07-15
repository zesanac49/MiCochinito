"""Recorrido E2E del flujo completo por la API real (TestClient + SQLite migrado
en memoria). Ejecuta el "camino feliz" de punta a punta y valida cada paso.

Uso:  PYTHONPATH=. python scripts/e2e.py
"""

from __future__ import annotations

import contextlib
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.shared.infrastructure.todos_los_modelos  # noqa: F401  (puebla metadata)
from app.core.config import Settings
from app.core.security import crear_access_token, hashear_password
from app.main import crear_app
from app.modules.natilleras.infrastructure.modelos import NatilleraModel
from app.shared.infrastructure.db import ModeloBase
from app.shared.infrastructure.modelos_auth import UsuarioModel, UsuarioNatilleraModel

_OK = "\033[1;32m[OK]\033[0m"
_FAIL = "\033[1;31m[FALLO]\033[0m"
_fallos = 0


def check(cond: bool, label: str, extra: str = "") -> None:
    global _fallos
    if cond:
        print(f"  {_OK} {label}")
    else:
        _fallos += 1
        print(f"  {_FAIL} {label}  {extra}")


SETTINGS = Settings(
    entorno="test", log_json=False,
    jwt_secret="secreto-de-prueba-suficientemente-largo-1234567890",
)

_CONFIG = {
    "valor_cuota": "90000.00",
    "periodicidad_cuota": "QUINCENAL",
    "dia_limite_pago": 5,
    "permite_aportes_extra": True,
    "tasa_interes_base": "2.0",
    "tasa_interes_min": "1.0",
    "tasa_interes_max": "3.0",
    "max_prestamos_activos": 2,
    "max_capital_vigente": "2000000.00",
    "estrategia_distribucion": "PROPORCIONAL_AHORRO",
    "valor_mora": "2000.00",
}


def main() -> int:
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    ModeloBase.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = crear_app(SETTINGS)
    app.state.engine = engine
    app.state.session_factory = factory
    c = TestClient(app, raise_server_exceptions=False)

    # Admin + token
    s = factory()
    admin = UsuarioModel(
        email="admin@e2e.co", hash_password=hashear_password("x"), nombre="Admin", activo=True
    )
    s.add(admin)
    s.commit()
    H = {"Authorization": f"Bearer {crear_access_token(SETTINGS, admin.uuid)}"}
    s.close()

    print("\n== Nivel 1: Natillera y configuración ==")
    r = c.post(
        "/api/v1/natilleras",
        json={
            "nombre": "Natillera E2E",
            "ciclo_inicio": "2026-01-01",
            "ciclo_fin": "2026-12-31",
            "configuracion": _CONFIG,
        },
        headers=H,
    )
    check(r.status_code == 201, "Crear natillera (quincenal, con valor_mora)", r.text)
    nat = r.json()["uuid"]
    base = f"/api/v1/natilleras/{nat}"
    check(
        c.get("/api/v1/auth/me", headers=H).json()["membresias"][0]["rol"] == "ADMINISTRADOR",
        "El creador queda ADMINISTRADOR",
    )
    check(c.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=H).status_code == 200,
          "Avanzar a ABIERTA")
    check(c.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=H).status_code == 200,
          "Avanzar a EN_OPERACION")
    periodos = c.get(f"{base}/periodos", headers=H).json()
    check(len(periodos) == 24, "Quincenal genera 24 sub-períodos (12 meses × 2)",
          f"got {len(periodos)}")
    check(sorted({p["secuencia"] for p in periodos}) == [1, 2], "Secuencias 1 y 2 por mes")

    print("\n== Nivel 2: Participantes y recaudo ==")
    ana = c.post(
        f"{base}/participantes",
        json={"nombre": "Ana", "tipo_documento": "CC", "numero_documento": "1010101010",
              "fecha_ingreso": "2026-01-10", "valor_cuota": "90000.00"},
        headers=H,
    ).json()
    check(ana.get("valor_cuota") == "90000.00", "Inscribir participante con cuota propia")
    per0 = periodos[0]["uuid"]
    pago = c.post(f"{base}/cuotas/pagos",
                  json={"participante_uuid": ana["uuid"], "periodo_uuid": per0}, headers=H)
    check(pago.status_code == 201 and pago.json()["monto"] == "45000.00",
          "Recaudo quincenal cobra la mitad (90.000 ÷ 2 = 45.000)",
          pago.text if pago.status_code != 201 else pago.json().get("monto", ""))
    dup = c.post(f"{base}/cuotas/pagos",
                 json={"participante_uuid": ana["uuid"], "periodo_uuid": per0}, headers=H)
    check(dup.status_code == 409, "No cobra doble el mismo período")

    print("\n== Nivel 3: Préstamos (interés) ==")
    pr = c.post(f"{base}/prestamos",
                json={"participante_uuid": ana["uuid"], "capital": "40000.00",
                      "tasa": "2.0", "plazo_meses": 6}, headers=H)
    check(pr.status_code == 201, "Solicitar préstamo", pr.text)
    pid = pr.json()["uuid"]
    check(c.post(f"{base}/prestamos/{pid}/aprobacion", json={"aprobar": True},
                 headers=H).status_code == 200, "Aprobar préstamo")
    check(c.post(f"{base}/prestamos/{pid}/desembolso", json={}, headers=H).status_code == 200,
          "Desembolsar (sale del Ahorro)")
    cuenta = c.get(f"{base}/participantes/{ana['uuid']}/cuenta", headers=H).json()
    check(cuenta["saldos"]["intereses_pendientes"] == "800.00",
          "Interés pendiente real en la cuenta (40.000 × 2% = 800)",
          cuenta["saldos"]["intereses_pendientes"])
    pagopr = c.post(f"{base}/prestamos/{pid}/pagos", json={"monto": "40800.00"}, headers=H)
    check(pagopr.status_code == 201, "Pagar préstamo (capital + interés)", pagopr.text)

    print("\n== Nivel 4: Multas y Polla ==")
    cat = c.post(f"{base}/catalogo-multas",
                 json={"nombre": "Retardo", "tipo": "OTRA", "valor": "10000"}, headers=H)
    check(cat.status_code == 201, "Crear catálogo de multa", cat.text)
    multa = c.post(f"{base}/multas",
                   json={"participante_uuid": ana["uuid"], "motivo": "Llegó tarde",
                         "catalogo_uuid": cat.json()["uuid"]}, headers=H)
    check(multa.status_code == 201, "Imponer multa", multa.text)
    check(c.post(f"{base}/multas/{multa.json()['uuid']}/pago", json={}, headers=H).status_code == 200,  # noqa: E501
          "Pagar multa (-> Rentabilidad)")
    act = c.post(f"{base}/actividades",
                 json={"tipo": "POLLA", "nombre": "Polla E2E", "periodo_uuid": per0,
                       "valor_numero": "5000", "cantidad_numeros": 10}, headers=H)
    check(act.status_code == 201, "Crear polla (sin campo premio)", act.text)
    a = f"{base}/actividades/{act.json()['uuid']}"
    c.put(f"{a}/numeros", json={"asignaciones": [{"numero": 1, "participante_uuid": ana["uuid"]}]},
          headers=H)
    c.post(f"{a}/apertura", headers=H)
    c.post(f"{a}/numeros/pagos", json={"numeros": [1]}, headers=H)
    det = c.get(a, headers=H).json()
    check(det["premio"] == "5000.00", "El premio es el pozo (valor × pagados)", det.get("premio", ""))  # noqa: E501
    sorteo = c.post(f"{a}/sorteo", json={"numero_ganador": 1, "fuente": "Lotería"}, headers=H).json()  # noqa: E501
    check(sorteo["sorteo"]["hubo_ganador"] is True, "Sorteo con ganador (número pagado)")
    cierre = c.post(f"{a}/cierre", headers=H)
    check(cierre.status_code == 200 and cierre.json()["utilidad"] == "0.00",
          "Cerrar: el ganador se lleva el pozo (utilidad 0)",
          cierre.text if cierre.status_code != 200 else cierre.json().get("utilidad", ""))

    print("\n== Nivel 7: Reportes y Liquidación ==")
    check(c.get(f"{base}/dashboard", headers=H).status_code == 200, "Dashboard/reportes responde")
    check(c.post(f"{base}/transiciones", json={"a": "PENDIENTE_LIQUIDACION"},
                 headers=H).status_code == 200, "Avanzar a PENDIENTE_LIQUIDACION")
    ini = c.post(f"{base}/liquidacion", headers=H)
    check(ini.status_code == 201, "Iniciar liquidación (sin bloqueos)", ini.text)
    calc = c.post(f"{base}/liquidacion/calculo", headers=H)
    check(calc.status_code == 200, "Calcular reparto (descuenta capital/interés/multas/mora)", calc.text)  # noqa: E501
    conf = c.post(f"{base}/liquidacion/confirmacion",
                  json={"nombre_natillera": "Natillera E2E"}, headers=H)
    check(conf.status_code == 200, "Confirmar con el nombre exacto → LIQUIDADA", conf.text)
    mal = c.get(f"{base}", headers=H).json()
    check(mal["estado"] == "LIQUIDADA", "La natillera queda LIQUIDADA")

    print("\n== Nivel 6: RBAC (supervisor no liquida) ==")
    s = factory()
    sup = UsuarioModel(email="sup@e2e.co", hash_password=hashear_password("x"),
                       nombre="Sup", activo=True)
    s.add(sup)
    s.flush()
    # Nueva natillera para el supervisor (la anterior está liquidada)
    s.commit()
    Hsup_admin = {"Authorization": f"Bearer {crear_access_token(SETTINGS, sup.uuid)}"}
    nat2 = c.post("/api/v1/natilleras",
                  json={"nombre": "Nat Sup", "ciclo_inicio": "2026-01-01",
                        "ciclo_fin": "2026-12-31", "configuracion": _CONFIG},
                  headers=Hsup_admin).json()["uuid"]
    # sup es admin de nat2; hacemos otro usuario supervisor de nat2
    otro = UsuarioModel(email="otro@e2e.co", hash_password=hashear_password("x"),
                        nombre="Otro", activo=True)
    s.add(otro)
    s.flush()
    nat2_id = s.scalar(select(NatilleraModel.id).where(NatilleraModel.uuid == nat2))
    s.add(UsuarioNatilleraModel(usuario_id=otro.id, natillera_id=nat2_id, rol="SUPERVISOR"))
    s.commit()
    Hotro = {"Authorization": f"Bearer {crear_access_token(SETTINGS, otro.uuid)}"}
    check(c.post(f"/api/v1/natilleras/{nat2}/liquidacion", headers=Hotro).status_code == 403,
          "El supervisor NO puede iniciar liquidación (403)")
    check(c.get(f"/api/v1/natilleras/{nat2}/participantes", headers=Hotro).status_code == 200,
          "El supervisor SÍ puede operar (ver participantes)")
    s.close()

    print()
    if _fallos == 0:
        print("\033[1;32m[E2E COMPLETO] Todos los pasos pasaron.\033[0m\n")
        return 0
    print(f"\033[1;31m[E2E] {_fallos} paso(s) fallaron.\033[0m\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
