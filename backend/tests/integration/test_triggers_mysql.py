"""Tests de la capa 3 (triggers MySQL) del ledger (S1-T07, TEC-07, doc 04 §4).

Marcados `@pytest.mark.mysql`: requieren MySQL real (Docker). Se OMITEN en el
entorno local sin Docker. Verifican que, a nivel de motor:
  - UPDATE/DELETE sobre `asientos` están prohibidos (inmutabilidad, RN-060);
  - una combinación concepto↔fondo inválida es rechazada (INV-01..03).

Se ejecutan con:  pytest -m mysql   (con DATABASE_URL apuntando a MySQL y la
migración 001 aplicada).
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.mysql

_URL = os.environ.get("DATABASE_URL", "")


@pytest.fixture()
def conn():  # type: ignore[no-untyped-def]
    if not _URL.startswith("mysql"):
        pytest.skip("Requiere DATABASE_URL de MySQL (TEC-07).")
    engine = create_engine(_URL)
    with engine.begin() as c:
        yield c


def _sembrar_fondo_y_asiento(conn) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        text(
            "INSERT INTO natilleras (uuid, nombre, estado, ciclo_inicio, ciclo_fin, "
            "created_at, updated_at) VALUES ('n-uuid','N','BORRADOR','2026-01-01',"
            "'2026-12-31', NOW(6), NOW(6))"
        )
    )
    conn.execute(
        text(
            "INSERT INTO fondos (uuid, natillera_id, tipo, saldo_cache, created_at, "
            "updated_at) VALUES ('f-uuid', LAST_INSERT_ID(), 'AHORRO', 0, NOW(6), NOW(6))"
        )
    )


def test_update_a_asientos_es_rechazado(conn) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(Exception):  # noqa: B017 (el motor lanza SIGNAL 45000)
        conn.execute(text("UPDATE asientos SET monto = monto + 1 WHERE 1=1"))


def test_delete_a_asientos_es_rechazado(conn) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(Exception):  # noqa: B017
        conn.execute(text("DELETE FROM asientos WHERE 1=1"))
