"""Tests del Unit of Work base: publicación de eventos al commit y rollback
en salida sin commit (S0-T05, RNF-03)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.eventbus import BusDeEventosEnMemoria
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.eventos import EventoDeDominio


@dataclass(frozen=True, slots=True)
class _AlgoPaso(EventoDeDominio):
    pass


class _AgregadoDemo(RaizDeAgregado):
    def hacer_algo(self) -> None:
        self.registrar_evento(_AlgoPaso(natillera_id=1))


class _UoWFake(UnidadDeTrabajo):
    """UoW en memoria que registra las llamadas de infraestructura."""

    def __init__(self, bus: BusDeEventosEnMemoria) -> None:
        super().__init__(bus)
        self.flushes = 0
        self.commits = 0
        self.rollbacks = 0

    def _flush(self) -> None:
        self.flushes += 1

    def _commit_transaccion(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def test_commit_publica_eventos_de_agregados_registrados() -> None:
    bus = BusDeEventosEnMemoria()
    recibidos: list[_AlgoPaso] = []
    bus.suscribir(_AlgoPaso, lambda e: recibidos.append(e))  # type: ignore[arg-type]

    uow = _UoWFake(bus)
    agg = _AgregadoDemo()
    agg.hacer_algo()
    uow.registrar(agg)
    uow.commit()

    assert len(recibidos) == 1
    assert uow.commits == 1
    assert uow.flushes >= 1


def test_salida_sin_commit_hace_rollback() -> None:
    bus = BusDeEventosEnMemoria()
    uow = _UoWFake(bus)
    with uow:
        pass
    assert uow.rollbacks == 1
    assert uow.commits == 0


def test_no_registra_dos_veces_el_mismo_agregado() -> None:
    bus = BusDeEventosEnMemoria()
    recibidos: list[_AlgoPaso] = []
    bus.suscribir(_AlgoPaso, lambda e: recibidos.append(e))  # type: ignore[arg-type]

    uow = _UoWFake(bus)
    agg = _AgregadoDemo()
    agg.hacer_algo()
    uow.registrar(agg)
    uow.registrar(agg)  # idempotente
    uow.commit()

    assert len(recibidos) == 1


def test_convergencia_bucle_infinito_de_handlers() -> None:
    """Un handler que reintroduce eventos sin fin debe abortar (no colgar)."""
    bus = BusDeEventosEnMemoria()
    uow = _UoWFake(bus)

    class _AgregadoMalo(RaizDeAgregado):
        def paso(self) -> None:
            self.registrar_evento(_AlgoPaso(natillera_id=1))

    agg = _AgregadoMalo()
    agg.paso()
    uow.registrar(agg)
    # El handler vuelve a poner un evento en el mismo agregado cada ronda.
    bus.suscribir(_AlgoPaso, lambda e: agg.registrar_evento(_AlgoPaso(natillera_id=1)))  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        uow.commit()
