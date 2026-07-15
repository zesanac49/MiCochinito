"""DTOs de participantes (doc 07)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.modules.participantes.domain.participante import (
    EstadoParticipante,
    Participante,
)
from app.shared.domain.documento import Documento, TipoDocumento


class InscribirParticipanteRequest(BaseModel):
    nombre: str = Field(min_length=1)
    tipo_documento: TipoDocumento
    numero_documento: str = Field(min_length=1)
    fecha_ingreso: date
    telefono: str | None = None
    direccion: str | None = None
    # Cuota mensual propia (opcional). Si se omite, se usa el default de la config.
    valor_cuota: str | None = None

    def documento(self) -> Documento:
        return Documento(self.tipo_documento, self.numero_documento)


class FijarCuotaRequest(BaseModel):
    valor_cuota: str = Field(min_length=1)


class EditarContactoRequest(BaseModel):
    telefono: str | None = None
    direccion: str | None = None


class CambiarEstadoRequest(BaseModel):
    estado: EstadoParticipante


class SaldosResponse(BaseModel):
    ahorros: str
    intereses_pendientes: str = "0.00"
    multas_pendientes: str = "0.00"
    mora_pendiente: str = "0.00"


class ParticipanteResponse(BaseModel):
    uuid: str
    nombre: str
    tipo_documento: str
    numero_documento: str
    estado: str
    fecha_ingreso: date
    telefono: str | None = None
    direccion: str | None = None
    valor_cuota: str | None = None

    @classmethod
    def de_dominio(cls, p: Participante) -> ParticipanteResponse:
        assert p.uuid is not None
        return cls(
            uuid=p.uuid,
            nombre=p.nombre,
            tipo_documento=p.documento.tipo.value,
            numero_documento=p.documento.numero,
            estado=p.estado.value,
            fecha_ingreso=p.fecha_ingreso,
            telefono=p.telefono,
            direccion=p.direccion,
            valor_cuota=p.valor_cuota.como_str() if p.valor_cuota is not None else None,
        )


class CuentaResponse(BaseModel):
    """Estado de cuenta del participante (RF-203): proyección del ledger."""

    participante_uuid: str
    saldos: SaldosResponse
    asientos: list[AsientoResponse]


# Import diferido para evitar ciclo con contabilidad.api.
from app.modules.contabilidad.api.schemas import AsientoResponse  # noqa: E402

CuentaResponse.model_rebuild()
