"""Siembra una natillera de demo lista para operar (usuario + config + fondos +
períodos + participantes). Requiere la BD ya migrada (alembic upgrade head).

Uso:  DATABASE_URL=... python scripts/seed_demo.py
Credenciales: admin@natillera.co / demo1234
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.shared.infrastructure.todos_los_modelos  # noqa: F401
from app.core.config import get_settings
from app.core.security import hashear_password
from app.modules.contabilidad.domain.periodos import calcular_periodos_mensuales
from app.modules.contabilidad.infrastructure.modelos import FondoModel, PeriodoModel
from app.modules.natilleras.infrastructure.modelos import (
    ConfiguracionModel,
    NatilleraModel,
)
from app.modules.participantes.infrastructure.modelos import ParticipanteModel
from app.shared.infrastructure.modelos_auth import UsuarioModel, UsuarioNatilleraModel

PARTICIPANTES = [
    ("Ana Pérez", "CC", "1010101010"),
    ("Beto Gómez", "CC", "2020202020"),
    ("Carla Ruiz", "CC", "3030303030"),
]


def sembrar(session: Session) -> None:
    if session.query(UsuarioModel).filter_by(email="admin@natillera.co").first():
        print("La demo ya está sembrada.")
        return

    usuario = UsuarioModel(
        email="admin@natillera.co",
        hash_password=hashear_password("demo1234"),
        nombre="Administrador Demo",
        activo=True,
    )
    session.add(usuario)
    session.flush()

    nat = NatilleraModel(
        nombre="Natillera Demo 2026",
        estado="EN_OPERACION",
        ciclo_inicio=date(2026, 1, 1),
        ciclo_fin=date(2026, 12, 31),
    )
    session.add(nat)
    session.flush()

    session.add_all(
        [
            FondoModel(natillera_id=nat.id, tipo="AHORRO", saldo_cache=0),
            FondoModel(natillera_id=nat.id, tipo="RENTABILIDAD", saldo_cache=0),
            ConfiguracionModel(
                natillera_id=nat.id,
                valor_cuota=Decimal("50000.00"),
                periodicidad_cuota="MENSUAL",
                dia_limite_pago=5,
                permite_aportes_extra=True,
                tasa_interes_base=Decimal("2.0"),
                tasa_interes_min=Decimal("1.0"),
                tasa_interes_max=Decimal("3.0"),
                max_prestamos_activos=2,
                max_capital_vigente=Decimal("2000000.00"),
                estrategia_distribucion="PROPORCIONAL_AHORRO",
                estrategia_congelada=False,
            ),
            UsuarioNatilleraModel(
                usuario_id=usuario.id, natillera_id=nat.id, rol="ADMINISTRADOR"
            ),
        ]
    )
    for anio, mes, fecha_limite in calcular_periodos_mensuales(
        date(2026, 1, 1), date(2026, 12, 31), 5
    ):
        session.add(
            PeriodoModel(
                natillera_id=nat.id, anio=anio, mes=mes,
                fecha_limite_cuota=fecha_limite, conciliado=False,
            )
        )
    for nombre, tipo_doc, doc in PARTICIPANTES:
        session.add(
            ParticipanteModel(
                natillera_id=nat.id, nombre=nombre, tipo_documento=tipo_doc,
                numero_documento=doc, estado="ACTIVO", fecha_ingreso=date(2026, 1, 10),
            )
        )
    session.commit()
    print("Demo sembrada: admin@natillera.co / demo1234")


if __name__ == "__main__":
    engine = create_engine(get_settings().database_url)
    with Session(engine) as s:
        sembrar(s)
