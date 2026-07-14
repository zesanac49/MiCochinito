"""DTOs de natilleras (doc 07). Montos como string decimal (TEC-01)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, field_validator

from app.modules.natilleras.domain.configuracion import (
    Configuracion,
    EstrategiaDistribucion,
    Periodicidad,
)
from app.modules.natilleras.domain.estados import EstadoNatillera
from app.modules.natilleras.domain.natillera import Natillera
from app.shared.domain.dinero import Dinero


class ConfiguracionRequest(BaseModel):
    valor_cuota: str
    periodicidad_cuota: Periodicidad
    dia_limite_pago: int = Field(ge=1, le=31)
    permite_aportes_extra: bool = False
    tasa_interes_base: str
    tasa_interes_min: str
    tasa_interes_max: str
    max_prestamos_activos: int = Field(ge=1, default=2)
    max_capital_vigente: str
    estrategia_distribucion: EstrategiaDistribucion

    @field_validator(
        "valor_cuota",
        "tasa_interes_base",
        "tasa_interes_min",
        "tasa_interes_max",
        "max_capital_vigente",
    )
    @classmethod
    def _decimal_valido(cls, v: str) -> str:
        try:
            Decimal(v)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("valor decimal inválido") from exc
        return v

    def a_dominio(self) -> Configuracion:
        return Configuracion(
            valor_cuota=Dinero(self.valor_cuota),
            periodicidad_cuota=self.periodicidad_cuota,
            dia_limite_pago=self.dia_limite_pago,
            permite_aportes_extra=self.permite_aportes_extra,
            tasa_interes_base=Decimal(self.tasa_interes_base),
            tasa_interes_min=Decimal(self.tasa_interes_min),
            tasa_interes_max=Decimal(self.tasa_interes_max),
            max_prestamos_activos=self.max_prestamos_activos,
            max_capital_vigente=Dinero(self.max_capital_vigente),
            estrategia_distribucion=self.estrategia_distribucion,
        )


class CrearNatilleraRequest(BaseModel):
    nombre: str = Field(min_length=1)
    ciclo_inicio: date
    ciclo_fin: date
    configuracion: ConfiguracionRequest | None = None


class TransicionRequest(BaseModel):
    a: EstadoNatillera


class ConfiguracionResponse(BaseModel):
    valor_cuota: str
    periodicidad_cuota: str
    dia_limite_pago: int
    permite_aportes_extra: bool
    tasa_interes_base: str
    tasa_interes_min: str
    tasa_interes_max: str
    max_prestamos_activos: int
    max_capital_vigente: str
    estrategia_distribucion: str
    estrategia_congelada: bool


class NatilleraResponse(BaseModel):
    uuid: str
    nombre: str
    estado: str
    ciclo_inicio: date
    ciclo_fin: date
    configuracion: ConfiguracionResponse | None = None

    @classmethod
    def de_dominio(cls, n: Natillera) -> NatilleraResponse:
        cfg = n.configuracion
        cfg_resp = (
            ConfiguracionResponse(
                valor_cuota=cfg.valor_cuota.como_str(),
                periodicidad_cuota=cfg.periodicidad_cuota.value,
                dia_limite_pago=cfg.dia_limite_pago,
                permite_aportes_extra=cfg.permite_aportes_extra,
                tasa_interes_base=str(cfg.tasa_interes_base),
                tasa_interes_min=str(cfg.tasa_interes_min),
                tasa_interes_max=str(cfg.tasa_interes_max),
                max_prestamos_activos=cfg.max_prestamos_activos,
                max_capital_vigente=cfg.max_capital_vigente.como_str(),
                estrategia_distribucion=cfg.estrategia_distribucion.value,
                estrategia_congelada=n.estrategia_congelada,
            )
            if cfg is not None
            else None
        )
        assert n.uuid is not None
        return cls(
            uuid=n.uuid,
            nombre=n.nombre,
            estado=n.estado.value,
            ciclo_inicio=n.ciclo_inicio,
            ciclo_fin=n.ciclo_fin,
            configuracion=cfg_resp,
        )
