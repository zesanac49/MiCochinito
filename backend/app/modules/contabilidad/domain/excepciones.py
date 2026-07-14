"""Excepciones del dominio contable (doc 05 §7, doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class ViolacionSeparacionDeFondos(ErrorDeDominio):
    """Un asiento intenta una combinación concepto/fondo/naturaleza prohibida
    por la matriz (INV-01..03). No debería alcanzarse desde la API; su presencia
    es una alerta (doc 07 §4)."""

    codigo = "VIOLACION_SEPARACION_FONDOS"


class SaldoInsuficiente(ErrorDeDominio):
    """Un egreso dejaría el fondo con saldo negativo (RN-007)."""

    codigo = "SALDO_INSUFICIENTE"
