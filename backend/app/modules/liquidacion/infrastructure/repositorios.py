"""Repositorio de liquidación (doc 05 §4)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.liquidacion.domain.liquidacion import (
    DetalleLiquidacion,
    FaseLiquidacion,
    Liquidacion,
)
from app.modules.liquidacion.infrastructure.modelos import (
    LiquidacionDecisionModel,
    LiquidacionDetalleModel,
    LiquidacionModel,
)
from app.shared.domain.dinero import Dinero


class RepositorioLiquidacionSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def obtener_por_natillera(self, natillera_id: int) -> Liquidacion | None:
        m = self._session.scalar(
            select(LiquidacionModel).where(LiquidacionModel.natillera_id == natillera_id)
        )
        return self._a_dominio(m) if m is not None else None

    def agregar(self, liquidacion: Liquidacion) -> Liquidacion:
        m = LiquidacionModel(
            natillera_id=self._natillera_id,
            estado=liquidacion.fase.value,
            estrategia_aplicada=liquidacion.estrategia_aplicada,
            saldo_rentabilidad_distribuido=liquidacion.saldo_rentabilidad_distribuido.monto,
        )
        self._session.add(m)
        self._session.flush()
        liquidacion._asignar_id(m.id)
        liquidacion.uuid = m.uuid
        self._reescribir_detalles(liquidacion, m.id)
        return liquidacion

    def guardar(self, liquidacion: Liquidacion) -> None:
        assert liquidacion.id is not None
        m = self._session.get(LiquidacionModel, liquidacion.id)
        if m is None or m.natillera_id != self._natillera_id:
            raise ValueError("Liquidación inexistente en el tenant.")
        m.estado = liquidacion.fase.value
        m.estrategia_aplicada = liquidacion.estrategia_aplicada
        m.saldo_rentabilidad_distribuido = liquidacion.saldo_rentabilidad_distribuido.monto
        if liquidacion.fase is FaseLiquidacion.CONFIRMADA and m.confirmada_en is None:
            m.confirmada_en = datetime.now(UTC)
        self._reescribir_detalles(liquidacion, liquidacion.id)

    def _reescribir_detalles(self, liquidacion: Liquidacion, liquidacion_id: int) -> None:
        self._session.execute(
            delete(LiquidacionDetalleModel).where(
                LiquidacionDetalleModel.liquidacion_id == liquidacion_id
            )
        )
        for d in liquidacion.detalles:
            self._session.add(
                LiquidacionDetalleModel(
                    natillera_id=self._natillera_id,
                    liquidacion_id=liquidacion_id,
                    participante_id=d.participante_id,
                    ahorros=d.ahorros.monto,
                    participacion_rentabilidad=d.participacion_rentabilidad.monto,
                    capital_pendiente=d.capital_pendiente.monto,
                    intereses_pendientes=d.intereses_pendientes.monto,
                    multas_pendientes=d.multas_pendientes.monto,
                    saldo_final=d.saldo_final.monto,
                )
            )

    def marcar_confirmada(self, liquidacion_id: int, usuario_id: int) -> None:
        m = self._session.get(LiquidacionModel, liquidacion_id)
        if m is not None:
            m.confirmada_por = usuario_id
            m.confirmada_en = datetime.now(UTC)

    def registrar_decision(
        self,
        liquidacion_id: int,
        tipo_bloqueo: str,
        origen_tipo: str,
        origen_id: int,
        decision: str,
        decidido_por: int,
    ) -> None:
        self._session.add(
            LiquidacionDecisionModel(
                natillera_id=self._natillera_id,
                liquidacion_id=liquidacion_id,
                tipo_bloqueo=tipo_bloqueo,
                origen_tipo=origen_tipo,
                origen_id=origen_id,
                decision=decision,
                decidido_por=decidido_por,
            )
        )

    def claves_decididas(self, liquidacion_id: int) -> set[tuple[str, str, int]]:
        filas = self._session.execute(
            select(
                LiquidacionDecisionModel.tipo_bloqueo,
                LiquidacionDecisionModel.origen_tipo,
                LiquidacionDecisionModel.origen_id,
            ).where(LiquidacionDecisionModel.liquidacion_id == liquidacion_id)
        ).all()
        return {(str(t), str(o), int(i)) for t, o, i in filas}

    def marcar_entregado(
        self, liquidacion_id: int, participante_id: int, usuario_id: int
    ) -> bool:
        d = self._session.scalar(
            select(LiquidacionDetalleModel).where(
                LiquidacionDetalleModel.liquidacion_id == liquidacion_id,
                LiquidacionDetalleModel.participante_id == participante_id,
            )
        )
        if d is None:
            return False
        d.entregado = True
        d.entregado_en = datetime.now(UTC)
        d.entregado_por = usuario_id
        return True

    def _a_dominio(self, m: LiquidacionModel) -> Liquidacion:
        detalles = [
            DetalleLiquidacion(
                participante_id=d.participante_id,
                ahorros=Dinero(d.ahorros),
                participacion_rentabilidad=Dinero(d.participacion_rentabilidad),
                capital_pendiente=Dinero(d.capital_pendiente),
                intereses_pendientes=Dinero(d.intereses_pendientes),
                multas_pendientes=Dinero(d.multas_pendientes),
            )
            for d in self._session.scalars(
                select(LiquidacionDetalleModel).where(
                    LiquidacionDetalleModel.liquidacion_id == m.id
                )
            ).all()
        ]
        return Liquidacion(
            natillera_id=m.natillera_id,
            fase=FaseLiquidacion(m.estado),
            estrategia_aplicada=m.estrategia_aplicada,
            saldo_rentabilidad_distribuido=Dinero(m.saldo_rentabilidad_distribuido),
            detalles=detalles,
            id=m.id,
            uuid=m.uuid,
        )
