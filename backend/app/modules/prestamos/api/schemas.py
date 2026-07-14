"""DTOs de préstamos (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.modules.contabilidad.api.schemas import AsientoResponse
from app.modules.prestamos.application.servicios import ResultadoPago
from app.modules.prestamos.domain.prestamo import Prestamo


def _valida_decimal(v: str) -> str:
    try:
        if Decimal(v) <= 0:
            raise ValueError("debe ser positivo")
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("valor decimal inválido") from exc
    return v


class SolicitarPrestamoRequest(BaseModel):
    participante_uuid: str
    capital: str
    tasa: str
    plazo_meses: int = Field(ge=1, le=120)

    _v_cap = field_validator("capital")(classmethod(lambda cls, v: _valida_decimal(v)))
    _v_tasa = field_validator("tasa")(classmethod(lambda cls, v: _valida_decimal(v)))


class AprobacionRequest(BaseModel):
    aprobar: bool
    motivo: str | None = None


class PagoPrestamoRequest(BaseModel):
    monto: str

    _v = field_validator("monto")(classmethod(lambda cls, v: _valida_decimal(v)))


class PrestamoResponse(BaseModel):
    uuid: str
    estado: str
    capital: str
    tasa: str
    plazo_meses: int
    saldo_capital: str
    fecha_desembolso: date | None
    motivo_rechazo: str | None

    @classmethod
    def de_dominio(cls, p: Prestamo) -> PrestamoResponse:
        assert p.uuid is not None
        return cls(
            uuid=p.uuid,
            estado=p.estado.value,
            capital=p.capital.como_str(),
            tasa=str(p.tasa.porcentaje),
            plazo_meses=p.plazo_meses,
            saldo_capital=p.saldo_capital.como_str(),
            fecha_desembolso=p.fecha_desembolso,
            motivo_rechazo=p.motivo_rechazo,
        )


class DescomposicionResponse(BaseModel):
    capital: str
    interes: str
    total: str


class PagoPrestamoResponse(BaseModel):
    descomposicion: DescomposicionResponse
    prestamo: PrestamoResponse
    asientos: list[AsientoResponse]

    @classmethod
    def de_resultado(cls, r: ResultadoPago) -> PagoPrestamoResponse:
        return cls(
            descomposicion=DescomposicionResponse(
                capital=r.descomposicion.capital.como_str(),
                interes=r.descomposicion.interes.como_str(),
                total=r.descomposicion.total.como_str(),
            ),
            prestamo=PrestamoResponse.de_dominio(r.prestamo),
            asientos=[AsientoResponse.de_leido(a) for a in r.asientos],
        )
