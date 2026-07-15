"""Repositorio de cuotas (doc 05 §4)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.contabilidad.infrastructure.modelos import PeriodoModel
from app.modules.cuotas.application.dtos import CuotaCreada
from app.modules.cuotas.domain.cuota import EstadoCuota
from app.modules.cuotas.infrastructure.modelos import CuotaModel
from app.shared.domain.dinero import Dinero


class RepositorioCuotasSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def existe_pagada(self, participante_id: int, periodo_id: int) -> bool:
        stmt = select(func.count()).select_from(CuotaModel).where(
            CuotaModel.natillera_id == self._natillera_id,
            CuotaModel.participante_id == participante_id,
            CuotaModel.periodo_id == periodo_id,
            CuotaModel.estado == EstadoCuota.PAGADA.value,
        )
        return (self._session.scalar(stmt) or 0) > 0

    def crear_pagada(
        self, participante_id: int, periodo_id: int, valor: Decimal
    ) -> CuotaCreada:
        cuota = CuotaModel(
            natillera_id=self._natillera_id,
            participante_id=participante_id,
            periodo_id=periodo_id,
            valor=valor,
            estado=EstadoCuota.PAGADA.value,
            pagada_en=datetime.now(UTC),
        )
        self._session.add(cuota)
        self._session.flush()
        return CuotaCreada(id=cuota.id, uuid=cuota.uuid)

    def enlazar_asiento(self, cuota_id: int, asiento_id: int | None) -> None:
        cuota = self._session.get(CuotaModel, cuota_id)
        if cuota is not None:
            cuota.asiento_id = asiento_id

    def mora_pendiente_de(
        self, participante_id: int, valor_mora: Dinero, hoy: date
    ) -> Dinero:
        """Mora acumulada del participante: por cada período vencido (fecha límite
        pasada) y no pagado, `valor_mora × semanas de atraso` (3B)."""
        if not valor_mora.es_positivo():
            return Dinero.cero()
        vencidos = self._session.execute(
            select(PeriodoModel.id, PeriodoModel.fecha_limite_cuota).where(
                PeriodoModel.natillera_id == self._natillera_id,
                PeriodoModel.fecha_limite_cuota.is_not(None),
                PeriodoModel.fecha_limite_cuota < hoy,
            )
        ).all()
        if not vencidos:
            return Dinero.cero()
        pagados = set(
            self._session.scalars(
                select(CuotaModel.periodo_id).where(
                    CuotaModel.natillera_id == self._natillera_id,
                    CuotaModel.participante_id == participante_id,
                    CuotaModel.estado == EstadoCuota.PAGADA.value,
                )
            ).all()
        )
        total = Dinero.cero()
        for periodo_id, fecha_limite in vencidos:
            if periodo_id in pagados or fecha_limite is None:
                continue
            semanas = (hoy - fecha_limite).days // 7
            if semanas > 0:
                total = total + valor_mora.multiplicado_por(semanas)
        return total
