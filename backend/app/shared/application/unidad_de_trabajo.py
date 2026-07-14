"""Unit of Work (puerto) — RNF-03, doc 05 §4.

Garantiza que TODOS los asientos de una operación financiera se persistan en una
sola transacción (o ninguno) y que los eventos de dominio acumulados por los
agregados se publiquen al commit, dentro de esa misma transacción.

Esta clase base concentra la lógica agnóstica de infraestructura (registro de
agregados y despacho de eventos). Las operaciones contra la base de datos
(`_flush`, `_commit_transaccion`, `rollback`) son abstractas y las implementa
`infrastructure` (Clean Arch: application no conoce SQLAlchemy).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from app.core.eventbus import BusDeEventos
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.eventos import EventoDeDominio

# Tope de rondas de despacho de eventos: evita bucles si un handler reintrodujera
# eventos indefinidamente. Un flujo real converge en 1-2 rondas.
_MAX_RONDAS_EVENTOS = 25


class UnidadDeTrabajo(ABC):
    """Contexto transaccional con publicación de eventos al commit."""

    def __init__(self, bus: BusDeEventos) -> None:
        self._bus = bus
        self._agregados: list[RaizDeAgregado] = []

    # --- Registro de agregados ---------------------------------------------
    def registrar(self, agregado: RaizDeAgregado) -> None:
        """Registra un agregado tocado en esta unidad de trabajo para que sus
        eventos se publiquen al commit. Los repositorios lo llaman al agregar o
        cargar un agregado."""
        if all(agregado is not a for a in self._agregados):
            self._agregados.append(agregado)

    # --- Context manager ----------------------------------------------------
    def __enter__(self) -> UnidadDeTrabajo:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Salida sin commit explícito => rollback (no se persiste nada a medias).
        self.rollback()

    # --- Confirmación -------------------------------------------------------
    def commit(self) -> None:
        """Persiste y publica eventos dentro de la misma transacción."""
        for _ in range(_MAX_RONDAS_EVENTOS):
            self._flush()  # asigna ids a los agregados nuevos antes de publicar
            eventos = self._extraer_eventos()
            if not eventos:
                break
            for evento in eventos:
                self._bus.publicar(evento)
        else:
            raise RuntimeError(
                "Despacho de eventos no convergió (posible bucle de handlers)."
            )
        self._commit_transaccion()
        self._agregados.clear()

    def _extraer_eventos(self) -> list[EventoDeDominio]:
        eventos: list[EventoDeDominio] = []
        for agregado in self._agregados:
            eventos.extend(agregado.extraer_eventos())
        return eventos

    # --- Puntos abstractos (los implementa infrastructure) -----------------
    @abstractmethod
    def _flush(self) -> None:
        """Vuelca cambios pendientes al motor (sin cerrar la transacción)."""

    @abstractmethod
    def _commit_transaccion(self) -> None:
        """Confirma la transacción del motor."""

    @abstractmethod
    def rollback(self) -> None:
        """Revierte la transacción del motor."""
