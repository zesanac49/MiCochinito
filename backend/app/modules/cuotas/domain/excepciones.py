"""Excepciones del dominio de cuotas (doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class PeriodoYaPagado(ErrorDeDominio):
    """El período ya tiene cuota pagada para el participante (idempotencia RF-301)."""

    codigo = "PERIODO_YA_PAGADO"
