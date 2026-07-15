"""Servicio de cuotas: pago individual, aporte extraordinario y lote (RF-301/302/303).

Contabilidad sigue siendo el único módulo que escribe asientos: este servicio
orquesta la cuota y delega el asiento en `ServicioContabilidad.registrar_asiento`.
"""

from __future__ import annotations

from app.core.errors import FuncionalidadNoDisponible, NoEncontrado
from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.puertos import RepositorioPeriodos
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.cuotas.application.dtos import (
    ItemLoteResultado,
    ResumenLote,
)
from app.modules.cuotas.application.puertos import RepositorioCuotas
from app.modules.cuotas.domain.excepciones import PeriodoYaPagado
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.modules.participantes.domain.participante import Participante
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


class ServicioCuotas:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        consulta_natillera: ConsultaNatillera,
        repo_participantes: RepositorioParticipantes,
        repo_periodos: RepositorioPeriodos,
        repo_cuotas: RepositorioCuotas,
        contabilidad: ServicioContabilidad,
    ) -> None:
        self._uow = uow
        self._consulta = consulta_natillera
        self._participantes = repo_participantes
        self._periodos = repo_periodos
        self._cuotas = repo_cuotas
        self._contabilidad = contabilidad

    def _participante(self, participante_uuid: str) -> Participante:
        p = self._participantes.obtener_por_uuid(participante_uuid)
        if p is None or p.id is None:
            raise NoEncontrado("Participante inexistente.")
        return p

    def _registrar_cuota(
        self, participante_id: int, periodo_id: int, valor: Dinero, autor_id: int
    ) -> AsientoLeido:
        cuota = self._cuotas.crear_pagada(participante_id, periodo_id, valor.monto)
        asiento = Asiento(
            monto=valor,
            naturaleza=Naturaleza.CREDITO,
            concepto=ConceptoContable.CUOTA_AHORRO,
            fondo=TipoFondo.AHORRO,
            referencia=ReferenciaOrigen(TipoOrigen.CUOTA, cuota.id),
            descripcion="Pago de cuota de ahorro",
            participante_id=participante_id,
            periodo_id=periodo_id,
        )
        leido = self._contabilidad.registrar_asiento(asiento, autor_id)
        self._cuotas.enlazar_asiento(cuota.id, leido.id)
        return leido

    def pagar_cuota(
        self, natillera_uuid: str, participante_uuid: str, periodo_uuid: str, autor_id: int
    ) -> AsientoLeido:
        with self._uow:
            datos = self._consulta.preparar_movimiento(natillera_uuid)
            participante = self._participante(participante_uuid)
            assert participante.id is not None
            periodo_id = self._periodos.obtener_id_por_uuid(periodo_uuid)
            if periodo_id is None:
                raise NoEncontrado("Período inexistente.")
            if self._cuotas.existe_pagada(participante.id, periodo_id):
                raise PeriodoYaPagado(
                    "El período ya está pagado para este participante."
                )
            mensual = participante.valor_cuota or datos.valor_cuota
            valor = mensual.dividir_entre(datos.cobros_por_mes)
            leido = self._registrar_cuota(
                participante.id, periodo_id, valor, autor_id
            )
            self._uow.commit()
        return leido

    def registrar_aporte(
        self, natillera_uuid: str, participante_uuid: str, monto: Dinero, autor_id: int
    ) -> AsientoLeido:
        with self._uow:
            datos = self._consulta.preparar_movimiento(natillera_uuid)
            if not datos.permite_aportes_extra:
                raise FuncionalidadNoDisponible(
                    "Los aportes extraordinarios no están habilitados en esta natillera."
                )
            participante = self._participante(participante_uuid)
            assert participante.id is not None
            asiento = Asiento(
                monto=monto,
                naturaleza=Naturaleza.CREDITO,
                concepto=ConceptoContable.APORTE_EXTRAORDINARIO,
                fondo=TipoFondo.AHORRO,
                referencia=ReferenciaOrigen(
                    TipoOrigen.APORTE_EXTRAORDINARIO, participante.id
                ),
                descripcion="Aporte extraordinario",
                participante_id=participante.id,
            )
            leido = self._contabilidad.registrar_asiento(asiento, autor_id)
            self._uow.commit()
        return leido

    def pagar_lote(
        self,
        natillera_uuid: str,
        items: list[tuple[str, str]],
        autor_id: int,
    ) -> ResumenLote:
        resultados: list[ItemLoteResultado] = []
        total = Dinero.cero()
        with self._uow:
            datos = self._consulta.preparar_movimiento(natillera_uuid)
            for participante_uuid, periodo_uuid in items:
                p = self._participantes.obtener_por_uuid(participante_uuid)
                periodo_id = self._periodos.obtener_id_por_uuid(periodo_uuid)
                if p is None or p.id is None or periodo_id is None:
                    resultados.append(
                        ItemLoteResultado(participante_uuid, periodo_uuid, "NO_ENCONTRADO")
                    )
                    continue
                if self._cuotas.existe_pagada(p.id, periodo_id):
                    resultados.append(
                        ItemLoteResultado(participante_uuid, periodo_uuid, "YA_PAGADO")
                    )
                    continue
                mensual = p.valor_cuota or datos.valor_cuota
                valor = mensual.dividir_entre(datos.cobros_por_mes)
                leido = self._registrar_cuota(p.id, periodo_id, valor, autor_id)
                total = total + valor
                resultados.append(
                    ItemLoteResultado(
                        participante_uuid, periodo_uuid, "PAGADO", leido.uuid
                    )
                )
            self._uow.commit()
        pagados = sum(1 for r in resultados if r.estado == "PAGADO")
        return ResumenLote(resultados, pagados, total.como_str())
