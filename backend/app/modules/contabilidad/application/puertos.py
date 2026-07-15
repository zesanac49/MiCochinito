"""Puertos (interfaces) del módulo contabilidad (doc 05 §4).

La capa application define estos Protocol; infrastructure los implementa. Así los
casos de uso se testean sin base de datos.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Protocol

from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import ConceptoContable, TipoFondo
from app.modules.contabilidad.domain.fondo import Fondo
from app.shared.domain.dinero import Dinero

if TYPE_CHECKING:
    from app.modules.contabilidad.application.servicios import ServicioContabilidad


class RepositorioFondos(Protocol):
    """Persistencia de fondos. Ligado a un tenant en su construcción."""

    def crear_par(self) -> None:
        """Crea los dos fondos (Ahorro y Rentabilidad) de la natillera (RN-001)."""
        ...

    def existe_par(self) -> bool: ...

    def id_de(self, tipo: TipoFondo) -> int | None: ...

    def cargar(self, tipo: TipoFondo) -> Fondo: ...

    def saldo(self, tipo: TipoFondo) -> Dinero: ...

    def actualizar_cache(self, tipo: TipoFondo, saldo: Dinero) -> None: ...


class RepositorioLedger(Protocol):
    """Ledger append-only (RN-060): sin update/delete."""

    def append(self, asiento: Asiento, fondo_id: int, creado_por: int) -> AsientoLeido: ...

    def obtener_por_uuid(self, uuid: str) -> AsientoLeido | None: ...

    def listar(
        self,
        *,
        fondo: TipoFondo | None = None,
        concepto: ConceptoContable | None = None,
        participante_id: int | None = None,
    ) -> list[AsientoLeido]: ...


class FabricaContabilidad(Protocol):
    """Construye un `ServicioContabilidad` ligado a un tenant. La usa otro módulo
    (natilleras) para crear los fondos de una natillera recién persistida."""

    def para(self, natillera_id: int) -> ServicioContabilidad: ...


class GeneradorPeriodos(Protocol):
    """Genera los períodos del ciclo (S2-T02). Idempotente: omite existentes."""

    def generar(
        self,
        natillera_id: int,
        ciclo_inicio: date,
        ciclo_fin: date,
        dia_limite: int,
        cobros_por_mes: int = 1,
    ) -> int: ...


class RepositorioPeriodos(Protocol):
    def obtener_id_por_uuid(self, uuid: str) -> int | None: ...
