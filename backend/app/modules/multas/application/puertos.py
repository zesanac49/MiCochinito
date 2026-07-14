"""Puertos del módulo multas (doc 05 §4)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.modules.multas.domain.multa import EstadoMulta, Multa
from app.shared.domain.dinero import Dinero


@dataclass(frozen=True, slots=True)
class EntradaCatalogo:
    id: int
    uuid: str
    nombre: str
    tipo: str
    valor: Decimal
    activo: bool


class RepositorioMultas(Protocol):
    def agregar(self, multa: Multa) -> Multa: ...

    def guardar(self, multa: Multa) -> None: ...

    def obtener_por_uuid(self, uuid: str) -> Multa | None: ...

    def registrar_pago(self, multa_id: int, asiento_id: int | None) -> None: ...

    def registrar_anulacion(self, multa_id: int, usuario_id: int) -> None: ...

    def listar(
        self, *, participante_id: int | None = None, estado: EstadoMulta | None = None
    ) -> list[Multa]: ...

    def total_pendientes_de(self, participante_id: int) -> Dinero:
        """Suma de multas IMPUESTAS del participante (cuenta por cobrar)."""
        ...


class RepositorioCatalogoMultas(Protocol):
    def crear(self, nombre: str, tipo: str, valor: Decimal) -> EntradaCatalogo: ...

    def listar(self) -> list[EntradaCatalogo]: ...

    def obtener(self, catalogo_id: int) -> EntradaCatalogo | None: ...

    def obtener_por_uuid(self, uuid: str) -> EntradaCatalogo | None: ...
