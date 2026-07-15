"""Servicio de aplicación de liquidación (RF-701..706).

Proceso: iniciar (pre-validaciones → bloqueos) → resolver bloqueos (decisión
auditada) → calcular (estrategia + fórmula RN-072) → confirmar (doble
verificación → asientos de cierre + natillera LIQUIDADA) → entregas.
"""

from __future__ import annotations

from datetime import date

from app.core.errors import NoEncontrado
from app.modules.actividades.application.puertos import RepositorioActividades
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.liquidacion.application.puertos import (
    ProveedorMoraCuotas,
    RepositorioLiquidacion,
)
from app.modules.liquidacion.domain.estrategias import (
    ParticipanteLiquidable,
    crear_estrategia,
)
from app.modules.liquidacion.domain.excepciones import LiquidacionBloqueada
from app.modules.liquidacion.domain.liquidacion import (
    Bloqueo,
    DetalleLiquidacion,
    Liquidacion,
)
from app.modules.multas.application.puertos import RepositorioMultas
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.modules.participantes.domain.participante import EstadoParticipante
from app.modules.prestamos.application.puertos import RepositorioPrestamos
from app.shared.application.auditoria import FabricaAuditoria
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


def _meses_permanencia(ingreso: date, hoy: date) -> int:
    meses = (hoy.year - ingreso.year) * 12 + (hoy.month - ingreso.month)
    return max(1, meses)


class ServicioLiquidacion:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        consulta: ConsultaNatillera,
        liquidacion: RepositorioLiquidacion,
        participantes: RepositorioParticipantes,
        prestamos: RepositorioPrestamos,
        multas: RepositorioMultas,
        actividades: RepositorioActividades,
        contabilidad: ServicioContabilidad,
        auditoria: FabricaAuditoria,
        mora_cuotas: ProveedorMoraCuotas,
    ) -> None:
        self._uow = uow
        self._consulta = consulta
        self._liq = liquidacion
        self._participantes = participantes
        self._prestamos = prestamos
        self._multas = multas
        self._actividades = actividades
        self._contabilidad = contabilidad
        self._auditoria = auditoria
        self._mora_cuotas = mora_cuotas

    # --- Bloqueos -----------------------------------------------------------
    def _bloqueos(self) -> list[Bloqueo]:
        bloqueos: list[Bloqueo] = []
        for pid in self._prestamos.ids_no_liquidables():
            bloqueos.append(
                Bloqueo("PRESTAMO_NO_PAGADO", "PRESTAMO", pid, "Préstamo sin liquidar")
            )
        for aid in self._actividades.ids_no_cerradas():
            bloqueos.append(
                Bloqueo("ACTIVIDAD_ABIERTA", "ACTIVIDAD", aid, "Actividad sin cerrar")
            )
        return bloqueos

    def _bloqueos_pendientes(self, liquidacion_id: int) -> list[Bloqueo]:
        decididas = self._liq.claves_decididas(liquidacion_id)
        return [b for b in self._bloqueos() if b.clave() not in decididas]

    def _cargar(self, natillera_id: int) -> Liquidacion:
        liq = self._liq.obtener_por_natillera(natillera_id)
        if liq is None:
            raise NoEncontrado("La liquidación no ha sido iniciada.")
        return liq

    # --- RF-701 -------------------------------------------------------------
    def iniciar(self, natillera_uuid: str) -> tuple[Liquidacion, list[Bloqueo]]:
        with self._uow:
            natillera = self._consulta.exigir_operacion(natillera_uuid, "LIQUIDAR")
            assert natillera.id is not None
            liq = self._liq.obtener_por_natillera(natillera.id)
            if liq is None:
                liq = Liquidacion(natillera.id)
                self._liq.agregar(liq)
            assert liq.id is not None
            bloqueos = self._bloqueos_pendientes(liq.id)
            self._uow.commit()
        return liq, bloqueos

    def obtener(self, natillera_uuid: str) -> tuple[Liquidacion | None, list[Bloqueo]]:
        natillera = self._consulta.exigir_operacion(natillera_uuid, "CONSULTAR")
        assert natillera.id is not None
        liq = self._liq.obtener_por_natillera(natillera.id)
        bloqueos = self._bloqueos_pendientes(liq.id) if liq and liq.id else self._bloqueos()
        return liq, bloqueos

    # --- RF-702 -------------------------------------------------------------
    def resolver_bloqueo(
        self,
        natillera_uuid: str,
        tipo_bloqueo: str,
        origen_tipo: str,
        origen_id: int,
        decision: str,
        autor: int,
    ) -> None:
        with self._uow:
            natillera = self._consulta.exigir_operacion(natillera_uuid, "LIQUIDAR")
            assert natillera.id is not None
            liq = self._cargar(natillera.id)
            assert liq.id is not None
            self._liq.registrar_decision(
                liq.id, tipo_bloqueo, origen_tipo, origen_id, decision, autor
            )
            self._auditoria.para(natillera.id).registrar(
                autor, "DECISION_LIQUIDACION", "LIQUIDACION", liq.id,
                {"bloqueo": tipo_bloqueo, "origen_id": origen_id, "decision": decision},
            )
            self._uow.commit()

    # --- RF-703 -------------------------------------------------------------
    def calcular(self, natillera_uuid: str, hoy: date) -> Liquidacion:
        with self._uow:
            natillera = self._consulta.exigir_operacion(natillera_uuid, "LIQUIDAR")
            assert natillera.id is not None and natillera.configuracion is not None
            liq = self._cargar(natillera.id)
            assert liq.id is not None
            pendientes = self._bloqueos_pendientes(liq.id)
            if pendientes:
                raise LiquidacionBloqueada(
                    "Hay bloqueos sin resolver.",
                    {"bloqueos": [b.descripcion for b in pendientes]},
                )
            estrategia_nombre = natillera.configuracion.estrategia_distribucion.value
            activos = self._participantes.listar(estado=EstadoParticipante.ACTIVO)
            fondo_rent = self._contabilidad.saldo(TipoFondo.RENTABILIDAD)
            ahorros = {
                p.id: self._contabilidad.saldo_participante(p.id, TipoFondo.AHORRO)
                for p in activos
                if p.id is not None
            }
            liquidables = [
                ParticipanteLiquidable(
                    p.id, ahorros[p.id], _meses_permanencia(p.fecha_ingreso, hoy)
                )
                for p in activos
                if p.id is not None
            ]
            participaciones = crear_estrategia(estrategia_nombre).distribuir(
                fondo_rent, liquidables
            )
            valor_mora = natillera.configuracion.valor_mora
            detalles = [
                DetalleLiquidacion(
                    participante_id=p.id,
                    ahorros=ahorros[p.id],
                    participacion_rentabilidad=participaciones.get(p.id, Dinero.cero()),
                    capital_pendiente=self._prestamos.capital_vigente_de(p.id),
                    intereses_pendientes=self._prestamos.interes_pendiente_de(p.id, hoy),
                    # Multas impuestas + mora de cuotas de ahorro atrasadas (3B).
                    multas_pendientes=self._multas.total_pendientes_de(p.id)
                    + self._mora_cuotas.mora_pendiente_de(p.id, valor_mora, hoy),
                )
                for p in activos
                if p.id is not None
            ]
            liq.registrar_calculo(estrategia_nombre, detalles, fondo_rent)
            self._liq.guardar(liq)
            self._uow.commit()
        return liq

    # --- RF-704 -------------------------------------------------------------
    def confirmar(self, natillera_uuid: str, nombre_ingresado: str, autor: int) -> Liquidacion:
        with self._uow:
            natillera = self._consulta.exigir_operacion(natillera_uuid, "LIQUIDAR")
            assert natillera.id is not None
            liq = self._cargar(natillera.id)
            assert liq.id is not None
            liq.confirmar(nombre_ingresado, natillera.nombre)
            for d in liq.detalles:
                if d.ahorros.es_positivo():
                    self._contabilidad.registrar_asiento(
                        self._asiento(
                            d.ahorros, ConceptoContable.DEVOLUCION_AHORRO, TipoFondo.AHORRO,
                            liq.id, d.participante_id, "Devolución de ahorros",
                        ),
                        autor,
                    )
                if d.participacion_rentabilidad.es_positivo():
                    self._contabilidad.registrar_asiento(
                        self._asiento(
                            d.participacion_rentabilidad,
                            ConceptoContable.DISTRIBUCION_RENTABILIDAD, TipoFondo.RENTABILIDAD,
                            liq.id, d.participante_id, "Distribución de rentabilidad",
                        ),
                        autor,
                    )
            self._liq.guardar(liq)
            self._liq.marcar_confirmada(liq.id, autor)
            self._consulta.transicionar_a(natillera_uuid, "LIQUIDADA")
            self._auditoria.para(natillera.id).registrar(
                autor, "CONFIRMACION_LIQUIDACION", "LIQUIDACION", liq.id
            )
            self._uow.commit()
        return liq

    # --- RF-706 -------------------------------------------------------------
    def registrar_entrega(self, natillera_uuid: str, participante_uuid: str, autor: int) -> None:
        with self._uow:
            natillera = self._consulta.exigir_operacion(natillera_uuid, "ENTREGAR_EFECTIVO")
            assert natillera.id is not None
            liq = self._cargar(natillera.id)
            assert liq.id is not None
            participante = self._participantes.obtener_por_uuid(participante_uuid)
            if participante is None or participante.id is None:
                raise NoEncontrado("Participante inexistente.")
            if not self._liq.marcar_entregado(liq.id, participante.id, autor):
                raise NoEncontrado("El participante no está en la liquidación.")
            self._uow.commit()

    def _asiento(
        self,
        monto: Dinero,
        concepto: ConceptoContable,
        fondo: TipoFondo,
        liquidacion_id: int,
        participante_id: int,
        descripcion: str,
    ) -> Asiento:
        return Asiento(
            monto=monto,
            naturaleza=Naturaleza.DEBITO,
            concepto=concepto,
            fondo=fondo,
            referencia=ReferenciaOrigen(TipoOrigen.LIQUIDACION, liquidacion_id),
            descripcion=descripcion,
            participante_id=participante_id,
        )
