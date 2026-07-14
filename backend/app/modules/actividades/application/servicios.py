"""Servicio de aplicación de actividades (RF-501..507).

El cierre traslada la utilidad al Fondo de Rentabilidad vía ServicioContabilidad
(`UTILIDAD_ACTIVIDAD` crédito si >0; `PERDIDA_ACTIVIDAD` débito si <0, con
pre-validación de saldo, RN-042a). Contabilidad sigue siendo el único que escribe
asientos.
"""

from __future__ import annotations

from datetime import date

from app.core.errors import NoEncontrado
from app.modules.actividades.application.puertos import RepositorioActividades
from app.modules.actividades.domain.actividad import Actividad
from app.modules.actividades.domain.estados import TipoActividad, TipoMovimiento
from app.modules.actividades.domain.excepciones import ActividadNoCerrable
from app.modules.contabilidad.application.puertos import RepositorioPeriodos
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


class ServicioActividades:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        consulta: ConsultaNatillera,
        actividades: RepositorioActividades,
        periodos: RepositorioPeriodos,
        participantes: RepositorioParticipantes,
        contabilidad: ServicioContabilidad,
    ) -> None:
        self._uow = uow
        self._consulta = consulta
        self._actividades = actividades
        self._periodos = periodos
        self._participantes = participantes
        self._contabilidad = contabilidad

    def _cargar(self, uuid: str) -> Actividad:
        a = self._actividades.obtener_por_uuid(uuid)
        if a is None:
            raise NoEncontrado("Actividad inexistente.")
        return a

    def _periodo_id(self, periodo_uuid: str) -> int:
        pid = self._periodos.obtener_id_por_uuid(periodo_uuid)
        if pid is None:
            raise NoEncontrado("Período inexistente.")
        return pid

    def _participante_id(self, uuid: str) -> int:
        p = self._participantes.obtener_por_uuid(uuid)
        if p is None or p.id is None:
            raise NoEncontrado("Participante inexistente.")
        return p.id

    # --- RF-501 -------------------------------------------------------------
    def crear(
        self,
        natillera_uuid: str,
        tipo: TipoActividad,
        nombre: str,
        periodo_uuid: str,
        valor_numero: Dinero | None,
        cantidad_numeros: int | None,
        premio: Dinero | None,
        fecha_sorteo: date | None,
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_ACTIVIDAD")
            actividad = Actividad.crear(
                tipo,
                nombre,
                self._periodo_id(periodo_uuid),
                valor_numero=valor_numero,
                cantidad_numeros=cantidad_numeros,
                premio=premio,
                fecha_sorteo=fecha_sorteo,
            )
            self._actividades.agregar(actividad)
            self._uow.commit()
        return actividad

    def abrir(self, natillera_uuid: str, actividad_uuid: str) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_ACTIVIDAD")
            actividad = self._cargar(actividad_uuid)
            actividad.abrir()
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    # --- RF-502 -------------------------------------------------------------
    def asignar_numeros(
        self, natillera_uuid: str, actividad_uuid: str, asignaciones: list[tuple[int, str]]
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "ASIGNAR_NUMEROS")
            actividad = self._cargar(actividad_uuid)
            for numero, participante_uuid in asignaciones:
                actividad.asignar_numero(numero, self._participante_id(participante_uuid))
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    # --- RF-503 -------------------------------------------------------------
    def registrar_pago_numeros(
        self, natillera_uuid: str, actividad_uuid: str, numeros: list[int]
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_ACTIVIDAD")
            actividad = self._cargar(actividad_uuid)
            for numero in numeros:
                actividad.marcar_pago_numero(numero)
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    # --- RF-504 -------------------------------------------------------------
    def registrar_movimiento(
        self,
        natillera_uuid: str,
        actividad_uuid: str,
        tipo: TipoMovimiento,
        concepto: str,
        valor: Dinero,
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_ACTIVIDAD")
            actividad = self._cargar(actividad_uuid)
            actividad.registrar_movimiento(tipo, concepto, valor)
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    # --- RF-505 -------------------------------------------------------------
    def sortear(
        self, natillera_uuid: str, actividad_uuid: str, numero_ganador: int, fuente: str
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "SORTEAR")
            actividad = self._cargar(actividad_uuid)
            actividad.sortear(numero_ganador, fuente)
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    # --- RF-506 -------------------------------------------------------------
    def cerrar(self, natillera_uuid: str, actividad_uuid: str, autor: int) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CERRAR_ACTIVIDAD")
            actividad = self._cargar(actividad_uuid)
            utilidad = actividad.utilidad()
            assert actividad.id is not None
            if utilidad.es_negativo():
                perdida = -utilidad
                if self._contabilidad.saldo(TipoFondo.RENTABILIDAD) < perdida:
                    raise ActividadNoCerrable(
                        "La rentabilidad acumulada es insuficiente para absorber la pérdida.",
                        {
                            "perdida": perdida.como_str(),
                            "saldo": self._contabilidad.saldo(TipoFondo.RENTABILIDAD).como_str(),
                        },
                    )
            actividad.cerrar()
            self._asiento_de_cierre(actividad.id, utilidad, autor)
            self._actividades.guardar(actividad)
            self._uow.commit()
        return actividad

    def _asiento_de_cierre(self, actividad_id: int, utilidad: Dinero, autor: int) -> None:
        if utilidad.es_cero():
            return
        if utilidad.es_positivo():
            concepto, naturaleza, monto = (
                ConceptoContable.UTILIDAD_ACTIVIDAD,
                Naturaleza.CREDITO,
                utilidad,
            )
        else:
            concepto, naturaleza, monto = (
                ConceptoContable.PERDIDA_ACTIVIDAD,
                Naturaleza.DEBITO,
                -utilidad,
            )
        self._contabilidad.registrar_asiento(
            Asiento(
                monto=monto,
                naturaleza=naturaleza,
                concepto=concepto,
                fondo=TipoFondo.RENTABILIDAD,
                referencia=ReferenciaOrigen(TipoOrigen.ACTIVIDAD, actividad_id),
                descripcion="Cierre de actividad",
            ),
            autor,
        )

    # --- RF-507 -------------------------------------------------------------
    def clonar(
        self, natillera_uuid: str, actividad_uuid: str, periodo_destino_uuid: str
    ) -> Actividad:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_ACTIVIDAD")
            original = self._cargar(actividad_uuid)
            clon = original.clonar_para(self._periodo_id(periodo_destino_uuid))
            self._actividades.agregar(clon)
            self._uow.commit()
        return clon
