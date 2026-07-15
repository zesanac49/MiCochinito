"""DTOs de contabilidad (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.contabilidad.application.dtos import (
    AsientoLeido,
    ReporteReconciliacion,
    SaldoFondo,
)
from app.modules.contabilidad.infrastructure.modelos import PeriodoModel


class AsientoResponse(BaseModel):
    uuid: str
    creado_en: datetime
    fondo: str
    naturaleza: str
    concepto: str
    monto: str
    descripcion: str
    origen_tipo: str
    origen_id: int
    participante_id: int | None = None

    @classmethod
    def de_leido(cls, a: AsientoLeido) -> AsientoResponse:
        return cls(
            uuid=a.uuid,
            creado_en=a.creado_en,
            fondo=a.fondo.value,
            naturaleza=a.naturaleza.value,
            concepto=a.concepto.value,
            monto=a.monto.como_str(),
            descripcion=a.descripcion,
            origen_tipo=a.origen_tipo,
            origen_id=a.origen_id,
            participante_id=a.participante_id,
        )


class FondoResponse(BaseModel):
    tipo: str
    saldo: str

    @classmethod
    def de_saldo(cls, s: SaldoFondo) -> FondoResponse:
        return cls(tipo=s.fondo.value, saldo=s.saldo.como_str())


class ReversionRequest(BaseModel):
    motivo: str = Field(min_length=3)


class LineaReconciliacionResponse(BaseModel):
    fondo: str
    saldo_ledger: str
    saldo_cache: str
    cuadra: bool


class ReconciliacionResponse(BaseModel):
    cuadra: bool
    lineas: list[LineaReconciliacionResponse]

    @classmethod
    def de_reporte(cls, r: ReporteReconciliacion) -> ReconciliacionResponse:
        return cls(
            cuadra=r.cuadra,
            lineas=[
                LineaReconciliacionResponse(
                    fondo=linea.fondo.value,
                    saldo_ledger=linea.saldo_ledger.como_str(),
                    saldo_cache=linea.saldo_cache.como_str(),
                    cuadra=linea.cuadra,
                )
                for linea in r.lineas
            ],
        )


class PeriodoResponse(BaseModel):
    uuid: str
    anio: int
    mes: int
    secuencia: int
    fecha_limite_cuota: date | None
    conciliado: bool

    @classmethod
    def de_modelo(cls, m: PeriodoModel) -> PeriodoResponse:
        return cls(
            uuid=m.uuid,
            anio=m.anio,
            mes=m.mes,
            secuencia=m.secuencia,
            fecha_limite_cuota=m.fecha_limite_cuota,
            conciliado=m.conciliado,
        )
