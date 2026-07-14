"""Repositorio de cuotas (doc 05 §4)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.cuotas.application.dtos import CuotaCreada
from app.modules.cuotas.domain.cuota import EstadoCuota
from app.modules.cuotas.infrastructure.modelos import CuotaModel


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
