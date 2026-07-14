"""Bases de entidad y agregado del dominio (doc 05 §2).

- `Entidad`: identidad por id (no por valor). Los value objects viven en sus
  propios módulos y usan igualdad por valor.
- `RaizDeAgregado`: entidad raíz que acumula eventos de dominio para que la
  capa de aplicación (UoW) los publique al hacer commit (TEC-05).

El dominio es Python puro: sin SQLAlchemy ni Pydantic aquí.
"""

from __future__ import annotations

from app.shared.domain.eventos import EventoDeDominio


class Entidad:
    """Entidad con identidad. La igualdad se define por (clase, id).

    El `id` puede ser None mientras la entidad aún no se persiste; en ese caso
    dos entidades nuevas nunca son iguales entre sí (identidad por objeto).
    """

    def __init__(self, id: int | None = None) -> None:
        self._id = id

    @property
    def id(self) -> int | None:
        return self._id

    def _asignar_id(self, id: int) -> None:
        """Asigna el id asignado por la persistencia. Solo una vez."""
        if self._id is not None:
            raise ValueError("El id de una entidad no puede reasignarse.")
        self._id = id

    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Entidad) or type(self) is not type(otro):
            return NotImplemented
        if self._id is None or otro._id is None:
            return self is otro
        return self._id == otro._id

    def __hash__(self) -> int:
        return hash((type(self).__name__, self._id)) if self._id is not None else id(self)


class RaizDeAgregado(Entidad):
    """Raíz de agregado: única puerta de entrada a un grupo de objetos y punto
    donde se registran los eventos de dominio a publicar."""

    def __init__(self, id: int | None = None) -> None:
        super().__init__(id)
        self._eventos: list[EventoDeDominio] = []

    def registrar_evento(self, evento: EventoDeDominio) -> None:
        self._eventos.append(evento)

    def extraer_eventos(self) -> list[EventoDeDominio]:
        """Devuelve y limpia los eventos acumulados (los toma el UoW al commit)."""
        eventos = self._eventos[:]
        self._eventos.clear()
        return eventos
