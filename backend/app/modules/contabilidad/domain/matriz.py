"""Matriz de conceptos contables (doc 02 §5) — la separación de fondos como dato.

Esta tabla ES el invariante INV-01..03 en forma verificable: para cada concepto
define qué fondo puede tocar y con qué naturaleza. Un `None` significa "ese
concepto no puede afectar ese fondo". Vive en un solo lugar y tiene tests
exhaustivos (concepto × fondo × naturaleza).

`REVERSION` es especial: no está en la matriz porque su fondo y naturaleza son
el espejo del asiento revertido (puede ser cualquier combinación válida). Se
valida aparte en `Fondo.validar_asiento` exigiendo `reversa_de`.
"""

from __future__ import annotations

from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)

C = ConceptoContable
F = TipoFondo
D = Naturaleza.DEBITO
Cr = Naturaleza.CREDITO

# concepto -> {fondo: naturaleza permitida | None}. (doc 02 §5)
MATRIZ: dict[ConceptoContable, dict[TipoFondo, Naturaleza | None]] = {
    C.CUOTA_AHORRO: {F.AHORRO: Cr, F.RENTABILIDAD: None},
    C.APORTE_EXTRAORDINARIO: {F.AHORRO: Cr, F.RENTABILIDAD: None},
    C.DESEMBOLSO_PRESTAMO: {F.AHORRO: D, F.RENTABILIDAD: None},
    C.RETORNO_CAPITAL: {F.AHORRO: Cr, F.RENTABILIDAD: None},
    C.INTERES_PAGADO: {F.AHORRO: None, F.RENTABILIDAD: Cr},
    C.UTILIDAD_ACTIVIDAD: {F.AHORRO: None, F.RENTABILIDAD: Cr},
    C.PERDIDA_ACTIVIDAD: {F.AHORRO: None, F.RENTABILIDAD: D},
    C.MULTA_PAGADA: {F.AHORRO: None, F.RENTABILIDAD: Cr},
    C.DEVOLUCION_AHORRO: {F.AHORRO: D, F.RENTABILIDAD: None},
    C.DISTRIBUCION_RENTABILIDAD: {F.AHORRO: None, F.RENTABILIDAD: D},
}


def naturaleza_permitida(
    concepto: ConceptoContable, fondo: TipoFondo
) -> Naturaleza | None:
    """Naturaleza permitida para (concepto, fondo), o None si está prohibido.

    `REVERSION` devuelve None aquí: no se resuelve por matriz sino por el
    asiento que revierte (ver `Fondo.validar_asiento`).
    """
    return MATRIZ.get(concepto, {}).get(fondo)
