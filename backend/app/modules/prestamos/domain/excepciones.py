"""Excepciones del dominio de préstamos (doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class TopePrestamosExcedido(ErrorDeDominio):
    """El participante ya tiene el máximo de préstamos activos (RN-037)."""

    codigo = "TOPE_PRESTAMOS_EXCEDIDO"


class TopeCapitalExcedido(ErrorDeDominio):
    """El capital vigente del participante excedería el tope (RN-038)."""

    codigo = "TOPE_CAPITAL_EXCEDIDO"


class PagoInvalido(ErrorDeDominio):
    """Pago inválido (p. ej. excede lo adeudado). Usa el código VALIDACION."""

    codigo = "VALIDACION"
