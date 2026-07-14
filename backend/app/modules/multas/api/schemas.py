"""DTOs de multas (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.modules.multas.application.puertos import EntradaCatalogo
from app.modules.multas.domain.multa import Multa


class CrearCatalogoRequest(BaseModel):
    nombre: str = Field(min_length=1)
    tipo: str  # MORA_CUOTA | MORA_PRESTAMO | MORA_ACTIVIDAD | OTRA
    valor: str

    @field_validator("valor")
    @classmethod
    def _valida(cls, v: str) -> str:
        try:
            if Decimal(v) <= 0:
                raise ValueError("positivo")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("valor inválido") from exc
        return v


class CatalogoResponse(BaseModel):
    uuid: str
    nombre: str
    tipo: str
    valor: str
    activo: bool

    @classmethod
    def de_entrada(cls, e: EntradaCatalogo) -> CatalogoResponse:
        return cls(
            uuid=e.uuid,
            nombre=e.nombre,
            tipo=e.tipo,
            valor=f"{e.valor:.2f}",
            activo=e.activo,
        )


class ImponerMultaRequest(BaseModel):
    participante_uuid: str
    motivo: str = Field(min_length=1)
    catalogo_uuid: str | None = None
    valor: str | None = None


class AnularMultaRequest(BaseModel):
    justificacion: str = Field(min_length=3)


class MultaResponse(BaseModel):
    uuid: str
    estado: str
    valor: str
    motivo: str
    justificacion_anulacion: str | None = None

    @classmethod
    def de_dominio(cls, m: Multa) -> MultaResponse:
        assert m.uuid is not None
        return cls(
            uuid=m.uuid,
            estado=m.estado.value,
            valor=m.valor.como_str(),
            motivo=m.motivo,
            justificacion_anulacion=m.justificacion_anulacion,
        )
