"""Casos de uso de participantes (RF-201/202, doc 05 §5)."""

from __future__ import annotations

from datetime import date

from app.core.errors import NoEncontrado
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.modules.participantes.domain.excepciones import DocumentoDuplicado
from app.modules.participantes.domain.participante import (
    EstadoParticipante,
    Participante,
)
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.documento import Documento


class InscribirParticipante:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        repo: RepositorioParticipantes,
        consulta_natillera: ConsultaNatillera,
    ) -> None:
        self._uow = uow
        self._repo = repo
        self._consulta = consulta_natillera

    def ejecutar(
        self,
        natillera_uuid: str,
        nombre: str,
        documento: Documento,
        fecha_ingreso: date,
        telefono: str | None = None,
        direccion: str | None = None,
        valor_cuota: Dinero | None = None,
    ) -> Participante:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "REGISTRAR_PARTICIPANTE")
            if self._repo.existe_documento(documento):
                raise DocumentoDuplicado(
                    "Ya existe un participante con ese documento.",
                    {"tipo": documento.tipo.value, "numero": documento.numero},
                )
            participante = Participante.inscribir(
                nombre, documento, fecha_ingreso, telefono, direccion, valor_cuota
            )
            self._repo.agregar(participante)
            self._uow.commit()
        return participante


class CambiarEstadoParticipante:
    def __init__(self, uow: UnidadDeTrabajo, repo: RepositorioParticipantes) -> None:
        self._uow = uow
        self._repo = repo

    def ejecutar(self, participante_uuid: str, hacia: EstadoParticipante) -> Participante:
        with self._uow:
            participante = self._repo.obtener_por_uuid(participante_uuid)
            if participante is None:
                raise NoEncontrado("Participante inexistente.")
            participante.cambiar_estado(hacia)
            self._repo.guardar(participante)
            self._uow.commit()
        return participante


class EditarContacto:
    def __init__(self, uow: UnidadDeTrabajo, repo: RepositorioParticipantes) -> None:
        self._uow = uow
        self._repo = repo

    def ejecutar(
        self, participante_uuid: str, telefono: str | None, direccion: str | None
    ) -> Participante:
        with self._uow:
            participante = self._repo.obtener_por_uuid(participante_uuid)
            if participante is None:
                raise NoEncontrado("Participante inexistente.")
            participante.editar_contacto(telefono, direccion)
            self._repo.guardar(participante)
            self._uow.commit()
        return participante


class FijarCuota:
    """Fija/cambia la cuota mensual propia de un participante (RF-301)."""

    def __init__(self, uow: UnidadDeTrabajo, repo: RepositorioParticipantes) -> None:
        self._uow = uow
        self._repo = repo

    def ejecutar(self, participante_uuid: str, valor: Dinero) -> Participante:
        with self._uow:
            participante = self._repo.obtener_por_uuid(participante_uuid)
            if participante is None:
                raise NoEncontrado("Participante inexistente.")
            participante.fijar_cuota(valor)
            self._repo.guardar(participante)
            self._uow.commit()
        return participante
