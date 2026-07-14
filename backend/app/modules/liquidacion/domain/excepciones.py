"""Excepciones del dominio de liquidación (doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class LiquidacionBloqueada(ErrorDeDominio):
    """Existen bloqueos sin resolver (préstamos activos, actividades abiertas...)."""

    codigo = "LIQUIDACION_BLOQUEADA"


class ConfirmacionIncorrecta(ErrorDeDominio):
    """La doble verificación (nombre de la natillera) no coincide (RF-704)."""

    codigo = "CONFIRMACION_INCORRECTA"
