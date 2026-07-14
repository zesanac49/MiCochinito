"""Repositorios de multas y catálogo (doc 05 §4).

El catálogo (`catalogo_multas`) se define en la migración 001 (módulo natilleras);
aquí se lee/escribe como composición del módulo multas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.multas.application.puertos import EntradaCatalogo
from app.modules.multas.domain.multa import EstadoMulta, Multa
from app.modules.multas.infrastructure.modelos import MultaModel
from app.modules.natilleras.infrastructure.modelos import CatalogoMultaModel
from app.shared.domain.dinero import Dinero


def _a_dominio(m: MultaModel) -> Multa:
    return Multa(
        participante_id=m.participante_id,
        valor=Dinero(m.valor),
        motivo=m.motivo,
        estado=EstadoMulta(m.estado),
        catalogo_multa_id=m.catalogo_multa_id,
        origen_tipo=m.origen_tipo,
        origen_id=m.origen_id,
        justificacion_anulacion=m.justificacion_anulacion,
        id=m.id,
        uuid=m.uuid,
    )


class RepositorioMultasSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def agregar(self, multa: Multa) -> Multa:
        m = MultaModel(
            natillera_id=self._natillera_id,
            participante_id=multa.participante_id,
            catalogo_multa_id=multa.catalogo_multa_id,
            valor=multa.valor.monto,
            motivo=multa.motivo,
            estado=multa.estado.value,
        )
        self._session.add(m)
        self._session.flush()
        multa._asignar_id(m.id)
        multa.uuid = m.uuid
        return multa

    def _cargar_modelo(self, multa_id: int) -> MultaModel:
        m = self._session.get(MultaModel, multa_id)
        if m is None or m.natillera_id != self._natillera_id:
            raise ValueError("Multa inexistente en el tenant.")
        return m

    def guardar(self, multa: Multa) -> None:
        assert multa.id is not None
        m = self._cargar_modelo(multa.id)
        m.estado = multa.estado.value
        m.justificacion_anulacion = multa.justificacion_anulacion

    def registrar_pago(self, multa_id: int, asiento_id: int | None) -> None:
        m = self._cargar_modelo(multa_id)
        m.asiento_id = asiento_id
        m.pagada_en = datetime.now(UTC)

    def registrar_anulacion(self, multa_id: int, usuario_id: int) -> None:
        m = self._cargar_modelo(multa_id)
        m.anulada_por = usuario_id

    def obtener_por_uuid(self, uuid: str) -> Multa | None:
        m = self._session.scalar(
            select(MultaModel).where(
                MultaModel.natillera_id == self._natillera_id, MultaModel.uuid == uuid
            )
        )
        return _a_dominio(m) if m is not None else None

    def listar(
        self, *, participante_id: int | None = None, estado: EstadoMulta | None = None
    ) -> list[Multa]:
        stmt = select(MultaModel).where(MultaModel.natillera_id == self._natillera_id)
        if participante_id is not None:
            stmt = stmt.where(MultaModel.participante_id == participante_id)
        if estado is not None:
            stmt = stmt.where(MultaModel.estado == estado.value)
        return [_a_dominio(m) for m in self._session.scalars(stmt.order_by(MultaModel.id)).all()]

    def total_pendientes_de(self, participante_id: int) -> Dinero:
        stmt = select(MultaModel.valor).where(
            MultaModel.natillera_id == self._natillera_id,
            MultaModel.participante_id == participante_id,
            MultaModel.estado == EstadoMulta.IMPUESTA.value,
        )
        total = Dinero.cero()
        for valor in self._session.scalars(stmt).all():
            total = total + Dinero(valor)
        return total


class RepositorioCatalogoMultasSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    @staticmethod
    def _a_entrada(m: CatalogoMultaModel) -> EntradaCatalogo:
        return EntradaCatalogo(
            id=m.id, uuid=m.uuid, nombre=m.nombre, tipo=m.tipo, valor=m.valor, activo=m.activo
        )

    def crear(self, nombre: str, tipo: str, valor: Decimal) -> EntradaCatalogo:
        m = CatalogoMultaModel(
            natillera_id=self._natillera_id, nombre=nombre, tipo=tipo, valor=valor, activo=True
        )
        self._session.add(m)
        self._session.flush()
        return self._a_entrada(m)

    def listar(self) -> list[EntradaCatalogo]:
        stmt = select(CatalogoMultaModel).where(
            CatalogoMultaModel.natillera_id == self._natillera_id
        )
        return [self._a_entrada(m) for m in self._session.scalars(stmt).all()]

    def obtener(self, catalogo_id: int) -> EntradaCatalogo | None:
        m = self._session.scalar(
            select(CatalogoMultaModel).where(
                CatalogoMultaModel.natillera_id == self._natillera_id,
                CatalogoMultaModel.id == catalogo_id,
            )
        )
        return self._a_entrada(m) if m is not None else None

    def obtener_por_uuid(self, uuid: str) -> EntradaCatalogo | None:
        m = self._session.scalar(
            select(CatalogoMultaModel).where(
                CatalogoMultaModel.natillera_id == self._natillera_id,
                CatalogoMultaModel.uuid == uuid,
            )
        )
        return self._a_entrada(m) if m is not None else None
