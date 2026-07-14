"""Excepciones del dominio de natilleras (doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class OperacionNoPermitidaEnEstado(ErrorDeDominio):
    """La operación no está permitida en el estado actual (matriz RN-081)."""

    codigo = "OPERACION_NO_PERMITIDA_EN_ESTADO"
