"""Máquina de estados de la natillera (INV-15, RN-080/081).

`TRANSICIONES` define los únicos avances válidos (sin saltos ni retrocesos).
`OPERACIONES_POR_ESTADO` es la matriz RN-081: qué operaciones permite cada
estado. Ambas son datos consultables por todos los módulos vía `Natillera.puede`.
"""

from __future__ import annotations

from enum import Enum


class EstadoNatillera(str, Enum):
    BORRADOR = "BORRADOR"
    ABIERTA = "ABIERTA"
    EN_OPERACION = "EN_OPERACION"
    PENDIENTE_LIQUIDACION = "PENDIENTE_LIQUIDACION"
    LIQUIDADA = "LIQUIDADA"
    ARCHIVADA = "ARCHIVADA"


class Operacion(str, Enum):
    """Operaciones de negocio sujetas a la matriz RN-081."""

    CONFIGURAR = "CONFIGURAR"
    REGISTRAR_PARTICIPANTE = "REGISTRAR_PARTICIPANTE"
    ASIGNAR_NUMEROS = "ASIGNAR_NUMEROS"
    MOVIMIENTO_FINANCIERO = "MOVIMIENTO_FINANCIERO"  # cuotas, aportes
    CREAR_PRESTAMO = "CREAR_PRESTAMO"
    CREAR_ACTIVIDAD = "CREAR_ACTIVIDAD"
    SORTEAR = "SORTEAR"
    COBRAR_CARTERA = "COBRAR_CARTERA"
    CERRAR_ACTIVIDAD = "CERRAR_ACTIVIDAD"
    LIQUIDAR = "LIQUIDAR"
    ENTREGAR_EFECTIVO = "ENTREGAR_EFECTIVO"
    CONSULTAR = "CONSULTAR"


E = EstadoNatillera
Op = Operacion

# Avances válidos (RN-080): solo hacia adelante, sin saltos.
TRANSICIONES: dict[EstadoNatillera, frozenset[EstadoNatillera]] = {
    E.BORRADOR: frozenset({E.ABIERTA}),
    E.ABIERTA: frozenset({E.EN_OPERACION}),
    E.EN_OPERACION: frozenset({E.PENDIENTE_LIQUIDACION}),
    E.PENDIENTE_LIQUIDACION: frozenset({E.LIQUIDADA}),
    E.LIQUIDADA: frozenset({E.ARCHIVADA}),
    E.ARCHIVADA: frozenset(),
}

# Matriz RN-081: operaciones permitidas por estado. CONSULTAR siempre permitido.
OPERACIONES_POR_ESTADO: dict[EstadoNatillera, frozenset[Operacion]] = {
    E.BORRADOR: frozenset({Op.CONFIGURAR, Op.REGISTRAR_PARTICIPANTE, Op.CONSULTAR}),
    E.ABIERTA: frozenset(
        {Op.REGISTRAR_PARTICIPANTE, Op.ASIGNAR_NUMEROS, Op.CONFIGURAR, Op.CONSULTAR}
    ),
    E.EN_OPERACION: frozenset(
        {
            Op.REGISTRAR_PARTICIPANTE,
            Op.ASIGNAR_NUMEROS,
            Op.MOVIMIENTO_FINANCIERO,
            Op.CREAR_PRESTAMO,
            Op.CREAR_ACTIVIDAD,
            Op.SORTEAR,
            Op.COBRAR_CARTERA,
            Op.CERRAR_ACTIVIDAD,
            Op.CONFIGURAR,
            Op.CONSULTAR,
        }
    ),
    E.PENDIENTE_LIQUIDACION: frozenset(
        {Op.COBRAR_CARTERA, Op.CERRAR_ACTIVIDAD, Op.SORTEAR, Op.LIQUIDAR, Op.CONSULTAR}
    ),
    E.LIQUIDADA: frozenset({Op.ENTREGAR_EFECTIVO, Op.CONSULTAR}),
    E.ARCHIVADA: frozenset({Op.CONSULTAR}),
}


def transicion_valida(desde: EstadoNatillera, hacia: EstadoNatillera) -> bool:
    return hacia in TRANSICIONES.get(desde, frozenset())


def operacion_permitida(estado: EstadoNatillera, operacion: Operacion) -> bool:
    return operacion in OPERACIONES_POR_ESTADO.get(estado, frozenset())
