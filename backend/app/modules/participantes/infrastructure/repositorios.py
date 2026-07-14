"""Repositorio y mapper de participantes (doc 05 §2/§4)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.participantes.domain.participante import (
    EstadoParticipante,
    Participante,
)
from app.modules.participantes.infrastructure.modelos import ParticipanteModel
from app.shared.domain.dinero import Dinero
from app.shared.domain.documento import Documento, TipoDocumento


def _a_dominio(m: ParticipanteModel) -> Participante:
    return Participante(
        nombre=m.nombre,
        documento=Documento(TipoDocumento(m.tipo_documento), m.numero_documento),
        fecha_ingreso=m.fecha_ingreso,
        estado=EstadoParticipante(m.estado),
        telefono=m.telefono,
        direccion=m.direccion,
        valor_cuota=Dinero(m.valor_cuota) if m.valor_cuota is not None else None,
        id=m.id,
        uuid=m.uuid,
    )


class RepositorioParticipantesSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def agregar(self, participante: Participante) -> Participante:
        m = ParticipanteModel(
            natillera_id=self._natillera_id,
            nombre=participante.nombre,
            tipo_documento=participante.documento.tipo.value,
            numero_documento=participante.documento.numero,
            telefono=participante.telefono,
            direccion=participante.direccion,
            estado=participante.estado.value,
            fecha_ingreso=participante.fecha_ingreso,
            valor_cuota=(
                participante.valor_cuota.monto
                if participante.valor_cuota is not None
                else None
            ),
        )
        self._session.add(m)
        self._session.flush()
        participante._asignar_id(m.id)
        participante.uuid = m.uuid
        return participante

    def guardar(self, participante: Participante) -> None:
        m = self._session.get(ParticipanteModel, participante.id)
        if m is None or m.natillera_id != self._natillera_id:
            raise ValueError("Participante inexistente en el tenant.")
        m.estado = participante.estado.value
        m.telefono = participante.telefono
        m.direccion = participante.direccion
        m.valor_cuota = (
            participante.valor_cuota.monto
            if participante.valor_cuota is not None
            else None
        )

    def obtener_por_uuid(self, uuid: str) -> Participante | None:
        m = self._session.scalar(
            select(ParticipanteModel).where(
                ParticipanteModel.natillera_id == self._natillera_id,
                ParticipanteModel.uuid == uuid,
            )
        )
        return _a_dominio(m) if m is not None else None

    def nombres_por_id(self, ids: list[int]) -> dict[int, tuple[str, str]]:
        """Mapa id -> (uuid, nombre) para enriquecer respuestas (p. ej. el acta)."""
        if not ids:
            return {}
        filas = self._session.execute(
            select(ParticipanteModel.id, ParticipanteModel.uuid, ParticipanteModel.nombre).where(
                ParticipanteModel.natillera_id == self._natillera_id,
                ParticipanteModel.id.in_(ids),
            )
        ).all()
        return {int(pid): (str(uuid), str(nombre)) for pid, uuid, nombre in filas}

    def existe_documento(self, documento: Documento) -> bool:
        stmt = select(func.count()).select_from(ParticipanteModel).where(
            ParticipanteModel.natillera_id == self._natillera_id,
            ParticipanteModel.tipo_documento == documento.tipo.value,
            ParticipanteModel.numero_documento == documento.numero,
        )
        return (self._session.scalar(stmt) or 0) > 0

    def listar(
        self, *, estado: EstadoParticipante | None = None, q: str | None = None
    ) -> list[Participante]:
        stmt = select(ParticipanteModel).where(
            ParticipanteModel.natillera_id == self._natillera_id
        )
        if estado is not None:
            stmt = stmt.where(ParticipanteModel.estado == estado.value)
        if q:
            stmt = stmt.where(ParticipanteModel.nombre.ilike(f"%{q}%"))
        stmt = stmt.order_by(ParticipanteModel.nombre)
        return [_a_dominio(m) for m in self._session.scalars(stmt).all()]
