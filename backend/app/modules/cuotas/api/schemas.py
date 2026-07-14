"""DTOs de cuotas (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.modules.cuotas.application.dtos import ItemLoteResultado, ResumenLote


class PagoCuotaRequest(BaseModel):
    participante_uuid: str
    periodo_uuid: str


class AporteRequest(BaseModel):
    participante_uuid: str
    monto: str

    @field_validator("monto")
    @classmethod
    def _decimal_positivo(cls, v: str) -> str:
        try:
            if Decimal(v) <= 0:
                raise ValueError("el monto debe ser positivo")
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("monto inválido") from exc
        return v


class ItemLoteRequest(BaseModel):
    participante_uuid: str
    periodo_uuid: str


class PagoLoteRequest(BaseModel):
    items: list[ItemLoteRequest] = Field(min_length=1)


class ItemLoteResponse(BaseModel):
    participante_uuid: str
    periodo_uuid: str
    estado: str
    asiento_uuid: str | None = None

    @classmethod
    def de_dto(cls, r: ItemLoteResultado) -> ItemLoteResponse:
        return cls(
            participante_uuid=r.participante_uuid,
            periodo_uuid=r.periodo_uuid,
            estado=r.estado,
            asiento_uuid=r.asiento_uuid,
        )


class ResumenLoteResponse(BaseModel):
    cantidad_pagados: int
    total_recaudado: str
    items: list[ItemLoteResponse]

    @classmethod
    def de_dto(cls, r: ResumenLote) -> ResumenLoteResponse:
        return cls(
            cantidad_pagados=r.cantidad_pagados,
            total_recaudado=r.total_recaudado,
            items=[ItemLoteResponse.de_dto(i) for i in r.items],
        )
