"""Idempotencia por header `Idempotency-Key` (doc 07 §1).

Misma clave + mismo payload → devuelve la referencia del resultado original
(replay). Misma clave + payload distinto → `ConflictoIdempotencia` (409).
El payload se normaliza a JSON ordenado y se hashea (sha256).
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictoIdempotencia
from app.shared.infrastructure.modelos_idempotencia import IdempotencyKeyModel


def hash_payload(payload: dict[str, object]) -> str:
    canonico = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class ServicioIdempotencia:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def buscar_replay(self, clave: str, payload: dict[str, object]) -> str | None:
        """Devuelve la referencia original si la clave ya se usó con el mismo
        payload; lanza `ConflictoIdempotencia` si el payload difiere; None si es
        nueva."""
        fila = self._session.scalar(
            select(IdempotencyKeyModel).where(
                IdempotencyKeyModel.natillera_id == self._natillera_id,
                IdempotencyKeyModel.clave == clave,
            )
        )
        if fila is None:
            return None
        if fila.hash_payload != hash_payload(payload):
            raise ConflictoIdempotencia(
                "La clave de idempotencia ya se usó con un payload distinto."
            )
        return fila.referencia_uuid

    def registrar(self, clave: str, payload: dict[str, object], referencia_uuid: str) -> None:
        self._session.add(
            IdempotencyKeyModel(
                natillera_id=self._natillera_id,
                clave=clave,
                hash_payload=hash_payload(payload),
                referencia_uuid=referencia_uuid,
            )
        )
