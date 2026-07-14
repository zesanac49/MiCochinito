"""Excepciones del dominio de actividades (doc 07 §4)."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class SorteoYaRegistrado(ErrorDeDominio):
    """El sorteo ya se registró y es inmutable (RF-505)."""

    codigo = "SORTEO_YA_REGISTRADO"


class NumeroNoDisponible(ErrorDeDominio):
    """El número ya está asignado a otro participante (RN-045)."""

    codigo = "NUMERO_NO_DISPONIBLE"


class ActividadNoCerrable(ErrorDeDominio):
    """No se puede cerrar (p. ej. pérdida sin saldo de Rentabilidad, RN-042a)."""

    codigo = "ACTIVIDAD_NO_CERRABLE"
