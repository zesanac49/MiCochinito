"""Tests del VO Documento y transiciones de Participante (S2-T01)."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.participantes.domain.participante import (
    EstadoParticipante,
    Participante,
)
from app.shared.domain.documento import Documento, TipoDocumento
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida


def test_documento_valido() -> None:
    d = Documento(TipoDocumento.CC, "1234567")
    assert d.numero == "1234567"
    assert d == Documento(TipoDocumento.CC, "1234567")


@pytest.mark.parametrize("numero", ["", "abc", "12"])
def test_documento_numerico_invalido(numero: str) -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        Documento(TipoDocumento.CC, numero)


def test_pasaporte_admite_alfanumerico() -> None:
    assert Documento(TipoDocumento.PP, "AB12345").numero == "AB12345"


def test_documento_inmutable() -> None:
    d = Documento(TipoDocumento.CC, "1234567")
    with pytest.raises(ErrorDeValidacionDeDominio):
        d._numero = "9"  # type: ignore[misc]


def _participante() -> Participante:
    return Participante.inscribir(
        "Ana", Documento(TipoDocumento.CC, "1234567"), date(2026, 1, 1)
    )


def test_transiciones_de_estado() -> None:
    p = _participante()
    assert p.estado is EstadoParticipante.ACTIVO
    p.cambiar_estado(EstadoParticipante.SUSPENDIDO)
    assert p.estado is EstadoParticipante.SUSPENDIDO
    p.cambiar_estado(EstadoParticipante.ACTIVO)
    p.cambiar_estado(EstadoParticipante.RETIRADO)
    assert p.estado is EstadoParticipante.RETIRADO


def test_retirado_es_terminal() -> None:
    p = _participante()
    p.cambiar_estado(EstadoParticipante.RETIRADO)
    with pytest.raises(TransicionInvalida):
        p.cambiar_estado(EstadoParticipante.ACTIVO)
