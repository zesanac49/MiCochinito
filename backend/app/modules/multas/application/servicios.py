"""Servicio de aplicación de multas (RF-601/602/603).

Solo el PAGO de una multa genera rentabilidad (INV-10): al pagar se registra
`MULTA_PAGADA` como crédito al Fondo de Rentabilidad vía ServicioContabilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.errors import NoEncontrado
from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.multas.application.puertos import (
    EntradaCatalogo,
    RepositorioCatalogoMultas,
    RepositorioMultas,
)
from app.modules.multas.domain.multa import Multa
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.shared.application.auditoria import FabricaAuditoria
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


@dataclass(frozen=True, slots=True)
class ResultadoPagoMulta:
    multa: Multa
    asiento: AsientoLeido


class ServicioMultas:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        consulta: ConsultaNatillera,
        participantes: RepositorioParticipantes,
        multas: RepositorioMultas,
        catalogo: RepositorioCatalogoMultas,
        contabilidad: ServicioContabilidad,
        auditoria: FabricaAuditoria,
    ) -> None:
        self._uow = uow
        self._consulta = consulta
        self._participantes = participantes
        self._multas = multas
        self._catalogo = catalogo
        self._contabilidad = contabilidad
        self._auditoria = auditoria

    def crear_catalogo(
        self, natillera_uuid: str, nombre: str, tipo: str, valor: Decimal
    ) -> EntradaCatalogo:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CONFIGURAR")
            entrada = self._catalogo.crear(nombre, tipo, valor)
            self._uow.commit()
        return entrada

    def imponer(
        self,
        natillera_uuid: str,
        participante_uuid: str,
        motivo: str,
        catalogo_multa_id: int | None,
        valor: Decimal | None,
    ) -> Multa:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "COBRAR_CARTERA")
            participante = self._participantes.obtener_por_uuid(participante_uuid)
            if participante is None or participante.id is None:
                raise NoEncontrado("Participante inexistente.")
            monto = self._resolver_valor(catalogo_multa_id, valor)
            multa = Multa.imponer(
                participante.id, monto, motivo, catalogo_multa_id=catalogo_multa_id
            )
            self._multas.agregar(multa)
            self._uow.commit()
        return multa

    def pagar(self, natillera_uuid: str, multa_uuid: str, autor: int) -> ResultadoPagoMulta:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "COBRAR_CARTERA")
            multa = self._multas.obtener_por_uuid(multa_uuid)
            if multa is None or multa.id is None:
                raise NoEncontrado("Multa inexistente.")
            multa.pagar()
            asiento = self._contabilidad.registrar_asiento(
                Asiento(
                    monto=multa.valor,
                    naturaleza=Naturaleza.CREDITO,
                    concepto=ConceptoContable.MULTA_PAGADA,
                    fondo=TipoFondo.RENTABILIDAD,
                    referencia=ReferenciaOrigen(TipoOrigen.MULTA, multa.id),
                    descripcion="Pago de multa",
                    participante_id=multa.participante_id,
                ),
                autor,
            )
            self._multas.registrar_pago(multa.id, asiento.id)
            self._multas.guardar(multa)
            self._uow.commit()
        return ResultadoPagoMulta(multa, asiento)

    def anular(
        self, natillera_uuid: str, multa_uuid: str, justificacion: str, autor: int
    ) -> Multa:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "COBRAR_CARTERA")
            multa = self._multas.obtener_por_uuid(multa_uuid)
            if multa is None or multa.id is None:
                raise NoEncontrado("Multa inexistente.")
            multa.anular(justificacion)
            self._multas.guardar(multa)
            self._multas.registrar_anulacion(multa.id, autor)
            self._auditoria.para(self._tenant(natillera_uuid)).registrar(
                autor, "ANULACION_MULTA", "MULTA", multa.id, {"justificacion": justificacion}
            )
            self._uow.commit()
        return multa

    # --- helpers ------------------------------------------------------------
    def _resolver_valor(self, catalogo_multa_id: int | None, valor: Decimal | None) -> Dinero:
        if catalogo_multa_id is not None:
            entrada = self._catalogo.obtener(catalogo_multa_id)
            if entrada is None:
                raise NoEncontrado("Entrada de catálogo de multas inexistente.")
            return Dinero(entrada.valor)
        if valor is not None:
            return Dinero(valor)
        raise ErrorDeValidacionDeDominio(
            "Debe indicarse una entrada del catálogo o un valor explícito."
        )

    def _tenant(self, natillera_uuid: str) -> int:
        return self._consulta.exigir_operacion(natillera_uuid, "CONSULTAR").id or 0
