"""Casos límite EXHAUSTIVOS de periodicidad, cuota dividida, recaudo y mora.

Cubre el dominio real:
- `app.modules.contabilidad.domain.periodos.calcular_periodos` (generación de
  sub-períodos por periodicidad, fechas límite acotadas, cruce de año, bisiesto).
- `Dinero.dividir_entre` (cuota mensual ÷ cobros por mes, con redondeo).
- Recaudo end-to-end (idempotencia, lote mixto, aportes según flag, estado).
- `RepositorioCuotasSQLAlchemy.mora_pendiente_de` (semanas de atraso, con `hoy`
  controlado y períodos sembrados vía `PeriodoModel`).

Valores esperados verificados ejecutando las funciones reales de dominio.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.contabilidad.domain.periodos import calcular_periodos
from app.modules.contabilidad.infrastructure.modelos import PeriodoModel
from app.modules.cuotas.domain.cuota import EstadoCuota
from app.modules.cuotas.infrastructure.modelos import CuotaModel
from app.modules.cuotas.infrastructure.repositorios import RepositorioCuotasSQLAlchemy
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorMonetario
from tests.conftest import bearer, crear_membresia, crear_natillera, crear_usuario
from tests.integration.test_cuotas_flujo import _CONFIG

# ===========================================================================
# 1) PERIODICIDAD / GENERACIÓN DE PERÍODOS
# ===========================================================================


@pytest.mark.parametrize(
    "inicio, fin, cobros, esperado",
    [
        ((2026, 1, 1), (2026, 12, 31), 1, 12),   # año completo mensual
        ((2026, 1, 1), (2026, 12, 31), 2, 24),   # año completo quincenal
        ((2026, 1, 1), (2026, 12, 31), 4, 48),   # año completo semanal
        ((2026, 3, 1), (2026, 3, 31), 1, 1),     # un solo mes mensual
        ((2026, 3, 1), (2026, 3, 31), 2, 2),     # un solo mes quincenal
        ((2026, 3, 1), (2026, 3, 31), 4, 4),     # un solo mes semanal
        ((2026, 12, 1), (2027, 1, 31), 1, 2),    # cruce dic→ene mensual
        ((2026, 12, 1), (2027, 1, 31), 2, 4),    # cruce dic→ene quincenal
        ((2026, 12, 1), (2027, 1, 31), 4, 8),    # cruce dic→ene semanal
        ((2026, 2, 1), (2026, 2, 28), 1, 1),     # febrero normal
        ((2028, 2, 1), (2028, 2, 29), 1, 1),     # febrero bisiesto
        ((2026, 12, 1), (2027, 2, 28), 1, 3),    # cruce de 3 meses
    ],
)
def test_count_exacto_por_periodicidad(
    inicio: tuple[int, int, int],
    fin: tuple[int, int, int],
    cobros: int,
    esperado: int,
) -> None:
    ps = calcular_periodos(date(*inicio), date(*fin), 5, cobros)
    assert len(ps) == esperado


@pytest.mark.parametrize(
    "inicio, fin",
    [
        ((2026, 1, 1), (2026, 12, 31)),
        ((2026, 12, 1), (2027, 2, 28)),
        ((2026, 6, 1), (2026, 6, 30)),
    ],
)
def test_mensual_secuencia_siempre_uno(
    inicio: tuple[int, int, int], fin: tuple[int, int, int]
) -> None:
    ps = calcular_periodos(date(*inicio), date(*fin), 5, 1)
    assert all(secuencia == 1 for (_a, _m, secuencia, _f) in ps)


@pytest.mark.parametrize(
    "anio, mes, dia_limite, dia_esp",
    [
        (2026, 1, 5, 5),       # día normal
        (2026, 1, 31, 31),     # 31 en mes de 31 días
        (2026, 2, 31, 28),     # 31 acotado a febrero normal
        (2028, 2, 31, 29),     # 31 acotado a febrero bisiesto
        (2026, 2, 29, 28),     # 29 acotado a febrero normal
        (2026, 2, 28, 28),     # último día exacto de febrero
        (2026, 2, 15, 15),     # mitad de febrero
        (2026, 4, 31, 30),     # 31 acotado a mes de 30 días
        (2026, 4, 30, 30),     # último día de abril
        (2026, 4, 15, 15),     # mitad de abril
        (2026, 6, 31, 30),     # 31 acotado a junio (30 días)
        (2026, 12, 31, 31),    # 31 en diciembre
    ],
)
def test_mensual_dia_limite_acotado(
    anio: int, mes: int, dia_limite: int, dia_esp: int
) -> None:
    ps = calcular_periodos(date(anio, mes, 1), date(anio, mes, 1), dia_limite, 1)
    assert len(ps) == 1
    _a, _m, _s, fecha = ps[0]
    assert (fecha.year, fecha.month, fecha.day) == (anio, mes, dia_esp)


@pytest.mark.parametrize(
    "anio, mes, q1, q2",
    [
        (2026, 1, 16, 31),    # 31 días
        (2026, 2, 14, 28),    # febrero normal
        (2028, 2, 14, 29),    # febrero bisiesto
        (2026, 4, 15, 30),    # 30 días
        (2026, 6, 15, 30),    # 30 días
        (2026, 11, 15, 30),   # 30 días
        (2026, 12, 16, 31),   # 31 días
    ],
)
def test_quincenal_fechas_limite(anio: int, mes: int, q1: int, q2: int) -> None:
    ps = calcular_periodos(date(anio, mes, 1), date(anio, mes, 1), 5, 2)
    dias = [f.day for (_a, _m, _s, f) in ps]
    assert dias == [q1, q2]           # 1ª ~mitad, 2ª último día
    assert q2 == calendar.monthrange(anio, mes)[1]  # 2ª quincena = último día


@pytest.mark.parametrize(
    "anio, mes, dias_esp",
    [
        (2026, 1, [8, 16, 23, 31]),    # 31 días
        (2026, 2, [7, 14, 21, 28]),    # febrero normal
        (2028, 2, [7, 14, 22, 29]),    # febrero bisiesto
        (2026, 4, [8, 15, 22, 30]),    # 30 días
        (2026, 6, [8, 15, 22, 30]),    # 30 días
        (2026, 12, [8, 16, 23, 31]),   # 31 días
        (2026, 3, [8, 16, 23, 31]),    # 31 días
    ],
)
def test_semanal_fechas_limite(anio: int, mes: int, dias_esp: list[int]) -> None:
    ps = calcular_periodos(date(anio, mes, 1), date(anio, mes, 1), 5, 4)
    dias = [f.day for (_a, _m, _s, f) in ps]
    assert dias == dias_esp


@pytest.mark.parametrize(
    "anio, mes, cobros",
    [
        (2026, 1, 2), (2026, 2, 2), (2028, 2, 2), (2026, 4, 2),
        (2026, 1, 4), (2026, 2, 4), (2028, 2, 4), (2026, 4, 4),
    ],
)
def test_ultima_secuencia_cae_ultimo_dia_del_mes(
    anio: int, mes: int, cobros: int
) -> None:
    ps = calcular_periodos(date(anio, mes, 1), date(anio, mes, 1), 5, cobros)
    ultima_fecha = ps[-1][3]
    assert ultima_fecha.day == calendar.monthrange(anio, mes)[1]


def test_ciclo_cruza_anio_mensual_secuencia_ordenada() -> None:
    ps = calcular_periodos(date(2026, 12, 1), date(2027, 1, 31), 5, 1)
    assert [(a, m) for (a, m, _s, _f) in ps] == [(2026, 12), (2027, 1)]


def test_ciclo_cruza_anio_quincenal_secuencia_ordenada() -> None:
    ps = calcular_periodos(date(2026, 12, 1), date(2027, 1, 31), 5, 2)
    assert [(a, m, s) for (a, m, s, _f) in ps] == [
        (2026, 12, 1),
        (2026, 12, 2),
        (2027, 1, 1),
        (2027, 1, 2),
    ]


# ===========================================================================
# 2) CUOTA DIVIDIDA (Dinero.dividir_entre)
# ===========================================================================


@pytest.mark.parametrize(
    "monto, divisor, esperado",
    [
        ("90000.00", 2, "45000.00"),     # quincenal exacta
        ("100000.00", 4, "25000.00"),    # semanal exacta
        ("50000.00", 1, "50000.00"),     # mensual (÷1)
        ("25.01", 2, "12.51"),           # impar ÷2, redondeo HALF_UP
        ("45000.01", 2, "22500.01"),     # impar ÷2, redondeo HALF_UP
        ("50001.00", 2, "25000.50"),     # impar ÷2 exacta en centavos
        ("1.00", 3, "0.33"),             # redondeo hacia abajo
        ("2.00", 3, "0.67"),             # redondeo hacia arriba
        ("0.01", 2, "0.01"),             # centavo ÷2, HALF_UP
        ("0.02", 4, "0.01"),             # 0.005 → HALF_UP
        ("10.00", 4, "2.50"),            # cuarta parte
        ("99999.99", 2, "50000.00"),     # 49999.995 → HALF_UP
        ("100.00", 7, "14.29"),          # divisor no trivial
        ("60000.00", 2, "30000.00"),     # quincenal de 60k
        ("60000.00", 4, "15000.00"),     # semanal de 60k
    ],
)
def test_dinero_dividir_entre(monto: str, divisor: int, esperado: str) -> None:
    assert Dinero(monto).dividir_entre(divisor).como_str() == esperado


@pytest.mark.parametrize("divisor", [0, -1, -5])
def test_dividir_entre_no_positivo_falla(divisor: int) -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("100.00").dividir_entre(divisor)


def test_dividir_entre_bool_falla() -> None:
    with pytest.raises(ErrorMonetario):
        Dinero("100.00").dividir_entre(True)


# ===========================================================================
# Helpers de integración (natillera operativa, inscripción, pago)
# ===========================================================================


def _operativa(
    client: TestClient,
    session: Session,
    periodicidad: str = "MENSUAL",
    valor_cuota: str = "50000.00",
    permite_aportes: bool = True,
) -> tuple[str, dict[str, str]]:
    u = crear_usuario(session)
    nat = crear_natillera(session)  # ciclo 2026-01-01 → 2026-12-31
    crear_membresia(session, u.id, nat.id)
    session.commit()
    h = bearer(u.uuid)
    base = f"/api/v1/natilleras/{nat.uuid}"
    cfg = {
        **_CONFIG,
        "periodicidad_cuota": periodicidad,
        "valor_cuota": valor_cuota,
        "permite_aportes_extra": permite_aportes,
    }
    client.put(f"{base}/configuracion", json=cfg, headers=h)
    client.post(f"{base}/transiciones", json={"a": "ABIERTA"}, headers=h)
    client.post(f"{base}/transiciones", json={"a": "EN_OPERACION"}, headers=h)
    return nat.uuid, h


def _inscribir(
    client: TestClient,
    nat: str,
    h: dict[str, str],
    doc: str,
    valor_cuota: str | None = None,
    nombre: str = "Ana",
) -> dict[str, object]:
    body: dict[str, object] = {
        "nombre": nombre,
        "tipo_documento": "CC",
        "numero_documento": doc,
        "fecha_ingreso": "2026-01-15",
    }
    if valor_cuota is not None:
        body["valor_cuota"] = valor_cuota
    r = client.post(f"/api/v1/natilleras/{nat}/participantes", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _periodos(client: TestClient, nat: str, h: dict[str, str]) -> list[dict[str, object]]:
    return client.get(f"/api/v1/natilleras/{nat}/periodos", headers=h).json()


def _pagar(client: TestClient, nat: str, h: dict[str, str], part: str, per: str):
    return client.post(
        f"/api/v1/natilleras/{nat}/cuotas/pagos",
        json={"participante_uuid": part, "periodo_uuid": per},
        headers=h,
    )


# ===========================================================================
# 3) CUOTA DIVIDIDA END-TO-END (cobra según periodicidad; propia vs default)
# ===========================================================================


@pytest.mark.parametrize(
    "periodicidad, cfg_cuota, propia, esperado",
    [
        ("MENSUAL", "60000.00", None, "60000.00"),        # default, ÷1
        ("QUINCENAL", "60000.00", None, "30000.00"),      # default, ÷2
        ("SEMANAL", "60000.00", None, "15000.00"),        # default, ÷4
        ("MENSUAL", "50000.00", "80000.00", "80000.00"),  # cuota propia, ÷1
        ("QUINCENAL", "50000.00", "90000.00", "45000.00"),  # propia ÷2
        ("SEMANAL", "50000.00", "100000.00", "25000.00"),   # propia ÷4
        ("SEMANAL", "50000.00", "90001.00", "22500.25"),    # propia impar ÷4
        ("QUINCENAL", "50001.00", None, "25000.50"),        # default impar ÷2
    ],
)
def test_cuota_dividida_por_periodicidad(
    client: TestClient,
    session: Session,
    periodicidad: str,
    cfg_cuota: str,
    propia: str | None,
    esperado: str,
) -> None:
    nat, h = _operativa(client, session, periodicidad, cfg_cuota)
    part = _inscribir(client, nat, h, "1010101010", valor_cuota=propia)
    per = str(_periodos(client, nat, h)[0]["uuid"])
    r = _pagar(client, nat, h, str(part["uuid"]), per)
    assert r.status_code == 201, r.text
    assert r.json()["monto"] == esperado


# ===========================================================================
# 4) RECAUDO: idempotencia, lote, aportes, estado
# ===========================================================================


@pytest.mark.parametrize("periodicidad", ["MENSUAL", "QUINCENAL", "SEMANAL"])
def test_doble_pago_mismo_periodo_es_409(
    client: TestClient, session: Session, periodicidad: str
) -> None:
    nat, h = _operativa(client, session, periodicidad)
    part = _inscribir(client, nat, h, "1010101010")
    per = str(_periodos(client, nat, h)[0]["uuid"])
    assert _pagar(client, nat, h, str(part["uuid"]), per).status_code == 201
    r = _pagar(client, nat, h, str(part["uuid"]), per)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "PERIODO_YA_PAGADO"


def test_idempotency_key_replica_mismo_asiento(
    client: TestClient, session: Session
) -> None:
    nat, h = _operativa(client, session)
    part = _inscribir(client, nat, h, "1010101010")
    per = str(_periodos(client, nat, h)[0]["uuid"])
    body = {"participante_uuid": part["uuid"], "periodo_uuid": per}
    h_idem = {**h, "Idempotency-Key": "edge-clave-1"}
    url = f"/api/v1/natilleras/{nat}/cuotas/pagos"
    r1 = client.post(url, json=body, headers=h_idem)
    r2 = client.post(url, json=body, headers=h_idem)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["uuid"] == r2.json()["uuid"]  # replay, no segundo pago


def test_lote_mixto_pagados_ya_pagados_no_encontrados(
    client: TestClient, session: Session
) -> None:
    nat, h = _operativa(client, session)
    ana = _inscribir(client, nat, h, "1010101010", valor_cuota="80000.00")
    pers = _periodos(client, nat, h)
    p0, p1 = str(pers[0]["uuid"]), str(pers[1]["uuid"])
    assert _pagar(client, nat, h, str(ana["uuid"]), p0).status_code == 201  # ya pagado
    items = [
        {"participante_uuid": ana["uuid"], "periodo_uuid": p0},          # YA_PAGADO
        {"participante_uuid": ana["uuid"], "periodo_uuid": p1},          # PAGADO
        {"participante_uuid": "no-existe", "periodo_uuid": p0},          # NO_ENCONTRADO
    ]
    r = client.post(
        f"/api/v1/natilleras/{nat}/cuotas/pagos-lote", json={"items": items}, headers=h
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["cantidad_pagados"] == 1
    assert res["total_recaudado"] == "80000.00"  # solo el nuevo (cuota propia)
    assert [i["estado"] for i in res["items"]] == [
        "YA_PAGADO",
        "PAGADO",
        "NO_ENCONTRADO",
    ]


def test_lote_total_es_suma_de_cuotas(client: TestClient, session: Session) -> None:
    nat, h = _operativa(client, session)
    ana = _inscribir(client, nat, h, "1010101010", valor_cuota="80000.00")
    beto = _inscribir(client, nat, h, "2020202020", nombre="Beto")  # default 50000
    per = str(_periodos(client, nat, h)[0]["uuid"])
    items = [
        {"participante_uuid": ana["uuid"], "periodo_uuid": per},
        {"participante_uuid": beto["uuid"], "periodo_uuid": per},
    ]
    r = client.post(
        f"/api/v1/natilleras/{nat}/cuotas/pagos-lote", json={"items": items}, headers=h
    )
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["cantidad_pagados"] == 2
    assert res["total_recaudado"] == "130000.00"  # 80000 + 50000


def test_aporte_extraordinario_bloqueado_sin_flag(
    client: TestClient, session: Session
) -> None:
    nat, h = _operativa(client, session, permite_aportes=False)
    part = _inscribir(client, nat, h, "1010101010")
    r = client.post(
        f"/api/v1/natilleras/{nat}/aportes-extraordinarios",
        json={"participante_uuid": part["uuid"], "monto": "100000.00"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "FUNCIONALIDAD_NO_DISPONIBLE"


def test_aporte_extraordinario_permitido_con_flag(
    client: TestClient, session: Session
) -> None:
    nat, h = _operativa(client, session, permite_aportes=True)
    part = _inscribir(client, nat, h, "1010101010")
    r = client.post(
        f"/api/v1/natilleras/{nat}/aportes-extraordinarios",
        json={"participante_uuid": part["uuid"], "monto": "100000.00"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    asiento = r.json()
    assert asiento["concepto"] == "APORTE_EXTRAORDINARIO"
    assert asiento["fondo"] == "AHORRO"
    assert asiento["monto"] == "100000.00"


def test_pago_en_borrador_bloqueado(client: TestClient, session: Session) -> None:
    # Sin llevar a EN_OPERACION (queda en BORRADOR): no se permite el movimiento.
    u = crear_usuario(session)
    nat = crear_natillera(session)
    crear_membresia(session, u.id, nat.id)
    session.commit()
    h = bearer(u.uuid)
    r = _pagar(client, nat.uuid, h, "cualquiera", "cualquiera")
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "OPERACION_NO_PERMITIDA_EN_ESTADO"


# ===========================================================================
# 5) MORA DE CUOTAS (mora_pendiente_de con `hoy` y períodos sembrados)
# ===========================================================================


def _sembrar_periodo(
    session: Session,
    natillera_id: int,
    limite: date,
    mes: int = 1,
    secuencia: int = 1,
    conciliado: bool = False,
) -> int:
    p = PeriodoModel(
        natillera_id=natillera_id,
        anio=2026,
        mes=mes,
        secuencia=secuencia,
        fecha_limite_cuota=limite,
        conciliado=conciliado,
    )
    session.add(p)
    session.flush()
    return p.id


@pytest.mark.parametrize(
    "atraso_dias, semanas",
    [
        (0, 0),    # vence hoy: 0 atraso
        (1, 0),    # 1 día
        (6, 0),    # 6 días < 1 semana
        (7, 1),    # exactamente 1 semana
        (8, 1),    # 8 días = 1 semana
        (13, 1),   # 13 días = 1 semana
        (14, 2),   # 2 semanas
        (20, 2),   # 20 días = 2 semanas
        (21, 3),   # 3 semanas
        (28, 4),   # 4 semanas
    ],
)
def test_mora_por_dias_de_atraso(
    session: Session, atraso_dias: int, semanas: int
) -> None:
    nat = crear_natillera(session)
    hoy = date(2026, 6, 15)
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=atraso_dias))
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    mora = repo.mora_pendiente_de(999, Dinero("2000"), hoy)
    assert mora == Dinero("2000").multiplicado_por(semanas)


def test_varios_periodos_vencidos_suman(session: Session) -> None:
    nat = crear_natillera(session)
    hoy = date(2026, 6, 15)
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=7), mes=1)    # 1 semana
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=14), mes=2)   # 2 semanas
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=21), mes=3)   # 3 semanas
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    mora = repo.mora_pendiente_de(999, Dinero("1000"), hoy)
    assert mora == Dinero("6000.00")  # (1 + 2 + 3) × 1000


def test_periodo_pagado_no_suma_mora(session: Session) -> None:
    nat = crear_natillera(session)
    hoy = date(2026, 6, 15)
    pagado = _sembrar_periodo(session, nat.id, hoy - timedelta(days=14), mes=1)
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=14), mes=2)  # sin pagar
    session.add(
        CuotaModel(
            natillera_id=nat.id,
            participante_id=7,
            periodo_id=pagado,
            valor=Dinero("50000").monto,
            estado=EstadoCuota.PAGADA.value,
        )
    )
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    # Solo cuenta el período no pagado (mes 2): 2 semanas × 1000.
    assert repo.mora_pendiente_de(7, Dinero("1000"), hoy) == Dinero("2000.00")


def test_periodo_futuro_no_genera_mora(session: Session) -> None:
    nat = crear_natillera(session)
    hoy = date(2026, 6, 15)
    _sembrar_periodo(session, nat.id, hoy + timedelta(days=10))  # aún no vence
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    assert repo.mora_pendiente_de(999, Dinero("1000"), hoy) == Dinero.cero()


def test_sin_valor_mora_es_cero(session: Session) -> None:
    nat = crear_natillera(session)
    hoy = date(2026, 6, 15)
    _sembrar_periodo(session, nat.id, hoy - timedelta(days=30))  # muy vencido
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    assert repo.mora_pendiente_de(999, Dinero.cero(), hoy) == Dinero.cero()
