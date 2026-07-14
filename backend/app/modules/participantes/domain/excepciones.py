"""Excepciones del dominio de participantes."""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio


class DocumentoDuplicado(ErrorDeDominio):
    """Ya existe un participante con ese documento en la natillera (RN-011).

    Usa el código `VALIDACION` del catálogo cerrado (doc 07 §4) para no
    introducir códigos nuevos.
    """

    codigo = "VALIDACION"
