"""Implementación de auditoría de acciones sobre `auditoria_acciones`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.shared.infrastructure.modelos_auditoria import AuditoriaAccionModel


class RegistroAuditoriaSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def registrar(
        self,
        usuario_id: int,
        accion: str,
        entidad_tipo: str,
        entidad_id: int | None = None,
        detalle: dict[str, object] | None = None,
    ) -> None:
        self._session.add(
            AuditoriaAccionModel(
                natillera_id=self._natillera_id,
                usuario_id=usuario_id,
                accion=accion,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                detalle=detalle,
            )
        )


class FabricaAuditoriaSQLAlchemy:
    def __init__(self, session: Session) -> None:
        self._session = session

    def para(self, natillera_id: int) -> RegistroAuditoriaSQLAlchemy:
        return RegistroAuditoriaSQLAlchemy(self._session, natillera_id)
