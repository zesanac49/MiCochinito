"""Mora de cuotas de ahorro: valor_mora × semanas de atraso (3B)."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.modules.contabilidad.infrastructure.modelos import PeriodoModel
from app.modules.cuotas.domain.cuota import EstadoCuota
from app.modules.cuotas.infrastructure.modelos import CuotaModel
from app.modules.cuotas.infrastructure.repositorios import RepositorioCuotasSQLAlchemy
from app.shared.domain.dinero import Dinero
from tests.conftest import crear_natillera


def _periodo(session: Session, nat_id: int, mes: int, limite: date) -> int:
    p = PeriodoModel(
        natillera_id=nat_id, anio=2026, mes=mes, secuencia=1,
        fecha_limite_cuota=limite, conciliado=False,
    )
    session.add(p)
    session.flush()
    return p.id


def test_mora_por_semanas_de_atraso(session: Session) -> None:
    nat = crear_natillera(session)
    _periodo(session, nat.id, 1, date(2026, 1, 5))   # vencido
    _periodo(session, nat.id, 2, date(2026, 2, 5))   # aún no vencido a la fecha
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    # A 2026-01-26: enero lleva 21 días de atraso = 3 semanas; febrero no ha vencido.
    mora = repo.mora_pendiente_de(999, Dinero("2000"), date(2026, 1, 26))
    assert mora == Dinero("6000.00")  # 3 semanas × 2.000


def test_periodo_pagado_no_genera_mora(session: Session) -> None:
    nat = crear_natillera(session)
    pid = _periodo(session, nat.id, 1, date(2026, 1, 5))
    session.add(
        CuotaModel(
            natillera_id=nat.id, participante_id=7, periodo_id=pid,
            valor=Dinero("50000").monto, estado=EstadoCuota.PAGADA.value,
        )
    )
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    assert repo.mora_pendiente_de(7, Dinero("2000"), date(2026, 3, 1)) == Dinero.cero()


def test_sin_valor_mora_es_cero(session: Session) -> None:
    nat = crear_natillera(session)
    _periodo(session, nat.id, 1, date(2026, 1, 5))
    session.commit()
    repo = RepositorioCuotasSQLAlchemy(session, nat.id)
    assert repo.mora_pendiente_de(999, Dinero.cero(), date(2026, 6, 1)) == Dinero.cero()
