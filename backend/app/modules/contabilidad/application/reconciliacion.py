"""Reconciliación de saldos (RF-802, RN-063).

Recalcula el saldo de cada fondo desde el ledger y lo compara con el caché
materializado. Un descuadre es un defecto crítico: se registra en auditoría (el
bloqueo preventivo de egresos del tenant se activa a partir de esta señal;
enforcement completo del bloqueo queda para endurecimiento, doc 09 Sprint 6).
"""

from __future__ import annotations

from typing import Protocol

from app.modules.contabilidad.application.dtos import (
    LineaReconciliacion,
    ReporteReconciliacion,
)
from app.modules.contabilidad.domain.conceptos import TipoFondo
from app.shared.domain.dinero import Dinero


class LecturaFondos(Protocol):
    def saldo(self, tipo: TipoFondo) -> Dinero: ...

    def saldo_cache(self, tipo: TipoFondo) -> Dinero: ...


class RegistroAuditoriaMin(Protocol):
    def registrar(
        self,
        usuario_id: int,
        accion: str,
        entidad_tipo: str,
        entidad_id: int | None = None,
        detalle: dict[str, object] | None = None,
    ) -> None: ...


class ServicioReconciliacion:
    def __init__(self, fondos: LecturaFondos, auditoria: RegistroAuditoriaMin) -> None:
        self._fondos = fondos
        self._auditoria = auditoria

    def reconciliar(self, autor_id: int) -> ReporteReconciliacion:
        lineas = [
            LineaReconciliacion(
                fondo=tipo,
                saldo_ledger=self._fondos.saldo(tipo),
                saldo_cache=self._fondos.saldo_cache(tipo),
            )
            for tipo in (TipoFondo.AHORRO, TipoFondo.RENTABILIDAD)
        ]
        reporte = ReporteReconciliacion(lineas)
        if not reporte.cuadra:
            self._auditoria.registrar(
                autor_id,
                "DESCUADRE_DETECTADO",
                "FONDO",
                None,
                {
                    linea.fondo.value: {
                        "ledger": linea.saldo_ledger.como_str(),
                        "cache": linea.saldo_cache.como_str(),
                    }
                    for linea in reporte.lineas
                    if not linea.cuadra
                },
            )
        return reporte
