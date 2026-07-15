"""Casos de uso de natilleras (RF-101/102/103, doc 05 §5).

Orquestan dominio + persistencia dentro de una transacción (UoW). CrearNatillera
crea también los dos fondos (RN-001) usando la fábrica de contabilidad (la
comunicación entre módulos pasa por la capa application del módulo dueño).
"""

from __future__ import annotations

from datetime import date

from app.core.errors import NoEncontrado
from app.modules.contabilidad.application.puertos import (
    FabricaContabilidad,
    GeneradorPeriodos,
)
from app.modules.natilleras.application.puertos import RepositorioNatilleras
from app.modules.natilleras.domain.configuracion import Configuracion
from app.modules.natilleras.domain.estados import EstadoNatillera, Operacion
from app.modules.natilleras.domain.natillera import Natillera
from app.shared.application.auditoria import FabricaAuditoria
from app.shared.application.membresias import AsignadorMembresia
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo


def _snapshot_config(cfg: Configuracion) -> dict[str, object]:
    """Serializa la configuración a JSON (montos como string, TEC-01)."""
    return {
        "valor_cuota": cfg.valor_cuota.como_str(),
        "periodicidad_cuota": cfg.periodicidad_cuota.value,
        "dia_limite_pago": cfg.dia_limite_pago,
        "permite_aportes_extra": cfg.permite_aportes_extra,
        "tasa_interes_base": str(cfg.tasa_interes_base),
        "tasa_interes_min": str(cfg.tasa_interes_min),
        "tasa_interes_max": str(cfg.tasa_interes_max),
        "max_prestamos_activos": cfg.max_prestamos_activos,
        "max_capital_vigente": cfg.max_capital_vigente.como_str(),
        "estrategia_distribucion": cfg.estrategia_distribucion.value,
        "valor_mora": cfg.valor_mora.como_str(),
    }


class CrearNatillera:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        repo: RepositorioNatilleras,
        fabrica_contabilidad: FabricaContabilidad,
        asignador: AsignadorMembresia,
    ) -> None:
        self._uow = uow
        self._repo = repo
        self._fabrica = fabrica_contabilidad
        self._asignador = asignador

    def ejecutar(
        self,
        nombre: str,
        ciclo_inicio: date,
        ciclo_fin: date,
        creador_id: int,
        configuracion: Configuracion | None = None,
    ) -> Natillera:
        with self._uow:
            natillera = Natillera.crear(nombre, ciclo_inicio, ciclo_fin)
            if configuracion is not None:
                natillera.configurar(configuracion)  # permitido en BORRADOR
            self._repo.agregar(natillera)  # flush asigna id/uuid
            assert natillera.id is not None
            self._fabrica.para(natillera.id).crear_fondos()  # RN-001
            # El creador queda ADMINISTRADOR para poder operar la natillera.
            if creador_id:
                self._asignador.asignar(creador_id, natillera.id, "ADMINISTRADOR")
            self._uow.commit()
        return natillera


class ConfigurarNatillera:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        repo: RepositorioNatilleras,
        fabrica_auditoria: FabricaAuditoria,
    ) -> None:
        self._uow = uow
        self._repo = repo
        self._auditoria = fabrica_auditoria

    def ejecutar(self, uuid: str, configuracion: Configuracion, autor_id: int) -> Natillera:
        with self._uow:
            natillera = self._repo.obtener_por_uuid(uuid)
            if natillera is None:
                raise NoEncontrado("Natillera inexistente.")
            natillera.configurar(configuracion)  # valida puede(CONFIGURAR)
            self._repo.guardar(natillera)
            assert natillera.id is not None
            self._repo.registrar_historial(
                natillera.id, _snapshot_config(configuracion), autor_id
            )
            self._auditoria.para(natillera.id).registrar(
                autor_id, "CAMBIO_CONFIG", "NATILLERA", natillera.id
            )
            self._uow.commit()
        return natillera


class TransicionarEstado:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        repo: RepositorioNatilleras,
        fabrica_auditoria: FabricaAuditoria,
        generador_periodos: GeneradorPeriodos,
    ) -> None:
        self._uow = uow
        self._repo = repo
        self._auditoria = fabrica_auditoria
        self._periodos = generador_periodos

    def ejecutar(self, uuid: str, hacia: EstadoNatillera, autor_id: int) -> Natillera:
        with self._uow:
            natillera = self._repo.obtener_por_uuid(uuid)
            if natillera is None:
                raise NoEncontrado("Natillera inexistente.")
            desde = natillera.estado
            natillera.transicionar(hacia)  # valida RN-080/081, emite evento
            self._repo.guardar(natillera)
            self._uow.registrar(natillera)  # publica NatilleraTransicionada
            assert natillera.id is not None
            # Al abrir, se generan los períodos del ciclo según la periodicidad.
            if hacia is EstadoNatillera.ABIERTA and natillera.configuracion is not None:
                self._periodos.generar(
                    natillera.id,
                    natillera.ciclo_inicio,
                    natillera.ciclo_fin,
                    natillera.configuracion.dia_limite_pago,
                    natillera.configuracion.periodicidad_cuota.cobros_por_mes(),
                )
            self._auditoria.para(natillera.id).registrar(
                autor_id,
                "TRANSICION_ESTADO",
                "NATILLERA",
                natillera.id,
                {"desde": desde.value, "hacia": hacia.value},
            )
            self._uow.commit()
        return natillera


class RegenerarPeriodos:
    """Sincroniza los períodos del ciclo con la periodicidad configurada
    (aditivo: crea los sub-períodos que falten; no borra ni toca lo ya cobrado)."""

    def __init__(
        self,
        uow: UnidadDeTrabajo,
        repo: RepositorioNatilleras,
        generador_periodos: GeneradorPeriodos,
    ) -> None:
        self._uow = uow
        self._repo = repo
        self._periodos = generador_periodos

    def ejecutar(self, uuid: str) -> int:
        with self._uow:
            natillera = self._repo.obtener_por_uuid(uuid)
            if natillera is None or natillera.id is None:
                raise NoEncontrado("Natillera inexistente.")
            natillera.exigir_puede(Operacion.CONFIGURAR)  # bloquea si está liquidada
            if natillera.configuracion is None:
                raise NoEncontrado("La natillera aún no tiene configuración.")
            creados = self._periodos.generar(
                natillera.id,
                natillera.ciclo_inicio,
                natillera.ciclo_fin,
                natillera.configuracion.dia_limite_pago,
                natillera.configuracion.periodicidad_cuota.cobros_por_mes(),
            )
            self._uow.commit()
        return creados
