"""Consultas de natillera para otros módulos (owner de RN-081, doc 05 §3).

Otros módulos (participantes, cuotas) verifican si una operación está permitida
en el estado actual llamando a `exigir_operacion` con el NOMBRE de la operación
(string), sin importar el enum interno `Operacion`. Así la matriz RN-081 vive en
un solo lugar y no se filtra el dominio de natilleras a otros módulos.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.core.errors import NoEncontrado
from app.modules.natilleras.application.puertos import RepositorioNatilleras
from app.modules.natilleras.domain.estados import Operacion
from app.modules.natilleras.domain.natillera import Natillera
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


@dataclass(frozen=True, slots=True)
class DatosNatilleraOperacion:
    """Datos que otros módulos necesitan para un movimiento financiero, sin
    exponer el agregado Natillera."""

    natillera_id: int
    valor_cuota: Dinero
    permite_aportes_extra: bool
    cobros_por_mes: int  # cuota por período = valor_cuota ÷ cobros_por_mes (RF-301)


@dataclass(frozen=True, slots=True)
class DatosPrestamo:
    """Parámetros de préstamo de la configuración (RN-031/037/038)."""

    natillera_id: int
    max_prestamos_activos: int
    max_capital_vigente: Dinero
    tasa_base: Decimal
    tasa_min: Decimal
    tasa_max: Decimal


class ConsultaNatillera:
    def __init__(self, repo: RepositorioNatilleras) -> None:
        self._repo = repo

    def exigir_operacion(self, natillera_uuid: str, operacion: str) -> Natillera:
        natillera = self._repo.obtener_por_uuid(natillera_uuid)
        if natillera is None:
            raise NoEncontrado("Natillera inexistente.")
        try:
            op = Operacion(operacion)
        except ValueError as exc:
            raise ErrorDeValidacionDeDominio(
                "Operación desconocida.", {"operacion": operacion}
            ) from exc
        natillera.exigir_puede(op)  # lanza OperacionNoPermitidaEnEstado si no aplica
        return natillera

    def transicionar_a(self, natillera_uuid: str, estado: str) -> Natillera:
        """Transiciona la natillera al estado dado (usa la sesión del caller; no
        hace commit). La usa liquidación para pasar a LIQUIDADA (RN-074)."""
        from app.modules.natilleras.domain.estados import EstadoNatillera

        natillera = self._repo.obtener_por_uuid(natillera_uuid)
        if natillera is None:
            raise NoEncontrado("Natillera inexistente.")
        natillera.transicionar(EstadoNatillera(estado))
        self._repo.guardar(natillera)
        return natillera

    def preparar_movimiento(self, natillera_uuid: str) -> DatosNatilleraOperacion:
        """Verifica que la natillera permita MOVIMIENTO_FINANCIERO y devuelve los
        datos necesarios (id, valor de cuota, si permite aportes extra)."""
        natillera = self.exigir_operacion(natillera_uuid, "MOVIMIENTO_FINANCIERO")
        if natillera.configuracion is None or natillera.id is None:
            raise ErrorDeValidacionDeDominio("La natillera no tiene configuración.")
        return DatosNatilleraOperacion(
            natillera_id=natillera.id,
            valor_cuota=natillera.configuracion.valor_cuota,
            permite_aportes_extra=natillera.configuracion.permite_aportes_extra,
            cobros_por_mes=natillera.configuracion.periodicidad_cuota.cobros_por_mes(),
        )

    def datos_para_prestamo(self, natillera_uuid: str, operacion: str) -> DatosPrestamo:
        """Verifica la operación de préstamo permitida y devuelve los topes y
        límites de tasa de la configuración."""
        natillera = self.exigir_operacion(natillera_uuid, operacion)
        cfg = natillera.configuracion
        if cfg is None or natillera.id is None:
            raise ErrorDeValidacionDeDominio("La natillera no tiene configuración.")
        return DatosPrestamo(
            natillera_id=natillera.id,
            max_prestamos_activos=cfg.max_prestamos_activos,
            max_capital_vigente=cfg.max_capital_vigente,
            tasa_base=cfg.tasa_interes_base,
            tasa_min=cfg.tasa_interes_min,
            tasa_max=cfg.tasa_interes_max,
        )
