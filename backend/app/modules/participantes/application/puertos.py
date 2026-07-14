"""Puertos del módulo participantes (doc 05 §4)."""

from __future__ import annotations

from typing import Protocol

from app.modules.participantes.domain.participante import EstadoParticipante, Participante
from app.shared.domain.documento import Documento


class RepositorioParticipantes(Protocol):
    """Ligado a un tenant en su construcción (TEC-02)."""

    def agregar(self, participante: Participante) -> Participante: ...

    def guardar(self, participante: Participante) -> None: ...

    def obtener_por_uuid(self, uuid: str) -> Participante | None: ...

    def existe_documento(self, documento: Documento) -> bool: ...

    def listar(
        self, *, estado: EstadoParticipante | None = None, q: str | None = None
    ) -> list[Participante]: ...
