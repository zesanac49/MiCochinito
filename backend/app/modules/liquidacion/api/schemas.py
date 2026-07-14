"""DTOs de liquidación (doc 07)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.liquidacion.domain.liquidacion import Bloqueo, Liquidacion


class BloqueoResponse(BaseModel):
    tipo: str
    origen_tipo: str
    origen_id: int
    descripcion: str


class DetalleResponse(BaseModel):
    participante_uuid: str
    participante_nombre: str
    ahorros: str
    participacion_rentabilidad: str
    capital_pendiente: str
    intereses_pendientes: str
    multas_pendientes: str
    saldo_final: str


class LiquidacionResponse(BaseModel):
    uuid: str | None
    fase: str
    estrategia_aplicada: str | None
    saldo_rentabilidad_distribuido: str
    detalles: list[DetalleResponse]
    bloqueos: list[BloqueoResponse]

    @classmethod
    def de_dominio(
        cls,
        liq: Liquidacion | None,
        bloqueos: list[Bloqueo],
        nombres: dict[int, tuple[str, str]],
    ) -> LiquidacionResponse:
        detalles = []
        if liq is not None:
            for d in liq.detalles:
                uuid, nombre = nombres.get(d.participante_id, ("", "?"))
                detalles.append(
                    DetalleResponse(
                        participante_uuid=uuid,
                        participante_nombre=nombre,
                        ahorros=d.ahorros.como_str(),
                        participacion_rentabilidad=d.participacion_rentabilidad.como_str(),
                        capital_pendiente=d.capital_pendiente.como_str(),
                        intereses_pendientes=d.intereses_pendientes.como_str(),
                        multas_pendientes=d.multas_pendientes.como_str(),
                        saldo_final=d.saldo_final.como_str(),
                    )
                )
        return cls(
            uuid=liq.uuid if liq else None,
            fase=liq.fase.value if liq else "PRE_VALIDACION",
            estrategia_aplicada=liq.estrategia_aplicada if liq else None,
            saldo_rentabilidad_distribuido=(
                liq.saldo_rentabilidad_distribuido.como_str() if liq else "0.00"
            ),
            detalles=detalles,
            bloqueos=[
                BloqueoResponse(
                    tipo=b.tipo, origen_tipo=b.origen_tipo, origen_id=b.origen_id,
                    descripcion=b.descripcion,
                )
                for b in bloqueos
            ],
        )


class DecisionRequest(BaseModel):
    tipo_bloqueo: str
    origen_tipo: str
    origen_id: int
    decision: str = Field(min_length=1)


class ConfirmacionRequest(BaseModel):
    nombre_natillera: str


class EntregaRequest(BaseModel):
    participante_uuid: str
