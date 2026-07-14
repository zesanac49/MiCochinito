"""DTOs de actividades (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.modules.actividades.domain.actividad import Actividad
from app.modules.actividades.domain.estados import TipoActividad, TipoMovimiento


class CrearActividadRequest(BaseModel):
    tipo: TipoActividad
    nombre: str = Field(min_length=1)
    periodo_uuid: str
    valor_numero: str | None = None
    cantidad_numeros: int | None = Field(default=None, ge=1, le=1000)
    fecha_sorteo: date | None = None


class AsignacionNumero(BaseModel):
    numero: int
    participante_uuid: str


class AsignarNumerosRequest(BaseModel):
    asignaciones: list[AsignacionNumero] = Field(min_length=1)


class PagoNumerosRequest(BaseModel):
    numeros: list[int] = Field(min_length=1)


class MovimientoRequest(BaseModel):
    tipo: TipoMovimiento
    concepto: str = Field(min_length=1)
    valor: str


class SorteoRequest(BaseModel):
    numero_ganador: int
    fuente: str = Field(min_length=1)


class ClonacionRequest(BaseModel):
    periodo_destino_uuid: str


class NumeroResponse(BaseModel):
    numero: int
    participante_id: int
    pagado: bool


class MovimientoResponse(BaseModel):
    tipo: str
    concepto: str
    valor: str


class SorteoResponse(BaseModel):
    numero_ganador: int
    hubo_ganador: bool
    participante_ganador_id: int | None
    fuente: str


class ActividadResponse(BaseModel):
    uuid: str
    tipo: str
    nombre: str
    estado: str
    valor_numero: str | None
    cantidad_numeros: int | None
    premio: str  # pozo actual = valor_numero × números pagados (calculado)
    fecha_sorteo: date | None
    utilidad: str
    numeros: list[NumeroResponse]
    movimientos: list[MovimientoResponse]
    sorteo: SorteoResponse | None

    @classmethod
    def de_dominio(cls, a: Actividad) -> ActividadResponse:
        assert a.uuid is not None
        s = a.sorteo
        return cls(
            uuid=a.uuid,
            tipo=a.tipo.value,
            nombre=a.nombre,
            estado=a.estado.value,
            valor_numero=a.valor_numero.como_str() if a.valor_numero else None,
            cantidad_numeros=a.cantidad_numeros,
            premio=a.premio_calculado().como_str(),
            fecha_sorteo=a.fecha_sorteo,
            utilidad=a.utilidad().como_str(),
            numeros=[
                NumeroResponse(numero=n.numero, participante_id=n.participante_id, pagado=n.pagado)
                for n in a.numeros
            ],
            movimientos=[
                MovimientoResponse(tipo=m.tipo.value, concepto=m.concepto, valor=m.valor.como_str())
                for m in a.movimientos
            ],
            sorteo=(
                SorteoResponse(
                    numero_ganador=s.numero_ganador,
                    hubo_ganador=s.hubo_ganador,
                    participante_ganador_id=s.participante_ganador_id,
                    fuente=s.fuente,
                )
                if s is not None
                else None
            ),
        )
