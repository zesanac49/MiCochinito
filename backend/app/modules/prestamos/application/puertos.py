"""Puertos del módulo préstamos (doc 05 §4)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from app.modules.prestamos.domain.prestamo import Prestamo
from app.shared.domain.dinero import Dinero


class RepositorioPrestamos(Protocol):
    def agregar(self, prestamo: Prestamo) -> Prestamo: ...

    def guardar(self, prestamo: Prestamo) -> None: ...

    def obtener_por_uuid(self, uuid: str) -> Prestamo | None: ...

    def cuenta_activos(self, participante_id: int) -> int: ...

    def capital_vigente_de(self, participante_id: int) -> Dinero: ...

    def listar(self, participante_id: int | None = None) -> list[Prestamo]: ...

    def en_pago(self) -> list[Prestamo]:
        """Préstamos EN_PAGO/EN_MORA (para el job de mora)."""
        ...

    def ids_no_liquidables(self) -> list[int]:
        """Ids de préstamos con estado distinto de PAGADO/RECHAZADO (bloqueos)."""
        ...


class RepositorioPrestamoPagos(Protocol):
    def registrar(
        self,
        prestamo_id: int,
        fecha: date,
        monto: Decimal,
        capital: Decimal,
        interes: Decimal,
        asiento_capital_id: int | None,
        asiento_interes_id: int | None,
    ) -> None: ...
