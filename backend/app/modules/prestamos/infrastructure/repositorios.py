"""Repositorios y mappers de préstamos (doc 05 §4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.prestamos.domain.estados import EstadoPrestamo
from app.modules.prestamos.domain.prestamo import Prestamo
from app.modules.prestamos.infrastructure.modelos import (
    PrestamoModel,
    PrestamoPagoModel,
)
from app.shared.domain.dinero import Dinero
from app.shared.domain.tasa import TasaInteres

# Estados que cuentan como préstamo activo (RN-037/038).
_ACTIVOS = (
    EstadoPrestamo.APROBADO.value,
    EstadoPrestamo.DESEMBOLSADO.value,
    EstadoPrestamo.EN_PAGO.value,
    EstadoPrestamo.EN_MORA.value,
)
_CON_SALDO = (
    EstadoPrestamo.DESEMBOLSADO.value,
    EstadoPrestamo.EN_PAGO.value,
    EstadoPrestamo.EN_MORA.value,
)


def _a_dominio(m: PrestamoModel) -> Prestamo:
    return Prestamo(
        participante_id=m.participante_id,
        capital=Dinero(m.capital),
        tasa=TasaInteres(Decimal(m.tasa_interes)),
        plazo_meses=m.plazo_meses,
        estado=EstadoPrestamo(m.estado),
        saldo_capital=Dinero(m.saldo_capital),
        fecha_desembolso=m.fecha_desembolso,
        motivo_rechazo=m.motivo_rechazo,
        id=m.id,
        uuid=m.uuid,
    )


class RepositorioPrestamosSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def agregar(self, prestamo: Prestamo) -> Prestamo:
        m = PrestamoModel(
            natillera_id=self._natillera_id,
            participante_id=prestamo.participante_id,
            capital=prestamo.capital.monto,
            tasa_interes=prestamo.tasa.porcentaje,
            plazo_meses=prestamo.plazo_meses,
            estado=prestamo.estado.value,
            saldo_capital=prestamo.saldo_capital.monto,
            fecha_desembolso=prestamo.fecha_desembolso,
            motivo_rechazo=prestamo.motivo_rechazo,
        )
        self._session.add(m)
        self._session.flush()
        prestamo._asignar_id(m.id)
        prestamo.uuid = m.uuid
        return prestamo

    def guardar(self, prestamo: Prestamo) -> None:
        m = self._session.get(PrestamoModel, prestamo.id)
        if m is None or m.natillera_id != self._natillera_id:
            raise ValueError("Préstamo inexistente en el tenant.")
        m.estado = prestamo.estado.value
        m.saldo_capital = prestamo.saldo_capital.monto
        m.fecha_desembolso = prestamo.fecha_desembolso
        m.motivo_rechazo = prestamo.motivo_rechazo

    def obtener_por_uuid(self, uuid: str) -> Prestamo | None:
        m = self._session.scalar(
            select(PrestamoModel).where(
                PrestamoModel.natillera_id == self._natillera_id,
                PrestamoModel.uuid == uuid,
            )
        )
        return _a_dominio(m) if m is not None else None

    def cuenta_activos(self, participante_id: int) -> int:
        stmt = select(func.count()).select_from(PrestamoModel).where(
            PrestamoModel.natillera_id == self._natillera_id,
            PrestamoModel.participante_id == participante_id,
            PrestamoModel.estado.in_(_ACTIVOS),
        )
        return int(self._session.scalar(stmt) or 0)

    def capital_vigente_de(self, participante_id: int) -> Dinero:
        stmt = select(PrestamoModel.saldo_capital).where(
            PrestamoModel.natillera_id == self._natillera_id,
            PrestamoModel.participante_id == participante_id,
            PrestamoModel.estado.in_(_CON_SALDO),
        )
        total = Dinero.cero()
        for saldo in self._session.scalars(stmt).all():
            total = total + Dinero(saldo)
        return total

    def listar(self, participante_id: int | None = None) -> list[Prestamo]:
        stmt = select(PrestamoModel).where(
            PrestamoModel.natillera_id == self._natillera_id
        )
        if participante_id is not None:
            stmt = stmt.where(PrestamoModel.participante_id == participante_id)
        stmt = stmt.order_by(PrestamoModel.id)
        return [_a_dominio(m) for m in self._session.scalars(stmt).all()]

    def en_pago(self) -> list[Prestamo]:
        stmt = select(PrestamoModel).where(
            PrestamoModel.natillera_id == self._natillera_id,
            PrestamoModel.estado.in_(
                (EstadoPrestamo.EN_PAGO.value, EstadoPrestamo.EN_MORA.value)
            ),
        )
        return [_a_dominio(m) for m in self._session.scalars(stmt).all()]

    def ids_no_liquidables(self) -> list[int]:
        stmt = select(PrestamoModel.id).where(
            PrestamoModel.natillera_id == self._natillera_id,
            PrestamoModel.estado.notin_(
                (EstadoPrestamo.PAGADO.value, EstadoPrestamo.RECHAZADO.value)
            ),
        )
        return list(self._session.scalars(stmt).all())


class RepositorioPrestamoPagosSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def registrar(
        self,
        prestamo_id: int,
        fecha: date,
        monto: Decimal,
        capital: Decimal,
        interes: Decimal,
        asiento_capital_id: int | None,
        asiento_interes_id: int | None,
    ) -> None:
        self._session.add(
            PrestamoPagoModel(
                natillera_id=self._natillera_id,
                prestamo_id=prestamo_id,
                fecha=fecha,
                monto_recibido=monto,
                componente_capital=capital,
                componente_interes=interes,
                asiento_capital_id=asiento_capital_id,
                asiento_interes_id=asiento_interes_id,
            )
        )
