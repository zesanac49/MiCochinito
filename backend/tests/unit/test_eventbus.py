"""Tests del bus de eventos síncrono en memoria (S0-T05)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.eventbus import BusDeEventosEnMemoria
from app.shared.domain.eventos import EventoDeDominio


@dataclass(frozen=True, slots=True)
class _EventoA(EventoDeDominio):
    dato: str = ""


@dataclass(frozen=True, slots=True)
class _EventoB(EventoDeDominio):
    pass


def test_publica_solo_a_handlers_del_tipo() -> None:
    bus = BusDeEventosEnMemoria()
    recibidos_a: list[_EventoA] = []
    recibidos_b: list[_EventoB] = []
    bus.suscribir(_EventoA, lambda e: recibidos_a.append(e))  # type: ignore[arg-type]
    bus.suscribir(_EventoB, lambda e: recibidos_b.append(e))  # type: ignore[arg-type]

    bus.publicar(_EventoA(natillera_id=1, dato="x"))

    assert len(recibidos_a) == 1
    assert recibidos_a[0].dato == "x"
    assert recibidos_b == []


def test_varios_handlers_mismo_evento() -> None:
    bus = BusDeEventosEnMemoria()
    contador = {"n": 0}
    bus.suscribir(_EventoA, lambda e: contador.__setitem__("n", contador["n"] + 1))  # type: ignore[arg-type]
    bus.suscribir(_EventoA, lambda e: contador.__setitem__("n", contador["n"] + 1))  # type: ignore[arg-type]

    bus.publicar(_EventoA(natillera_id=1))

    assert contador["n"] == 2


def test_sin_handlers_no_falla() -> None:
    BusDeEventosEnMemoria().publicar(_EventoA(natillera_id=1))
