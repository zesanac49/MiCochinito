"""Cálculo de períodos del ciclo (doc 04 §3.4, S2-T02).

Los períodos son mensuales (la tabla es UNIQUE(natillera, anio, mes)). Al abrir
la natillera se generan los períodos desde el inicio hasta el fin del ciclo, cada
uno con su fecha límite de cuota (el día configurado, acotado al último día del
mes).
"""

from __future__ import annotations

import calendar
from datetime import date


def calcular_periodos_mensuales(
    ciclo_inicio: date, ciclo_fin: date, dia_limite: int
) -> list[tuple[int, int, date]]:
    """Devuelve [(anio, mes, fecha_limite_cuota)] para cada mes del ciclo
    (periodicidad mensual). Se conserva por compatibilidad."""
    periodos: list[tuple[int, int, date]] = []
    anio, mes = ciclo_inicio.year, ciclo_inicio.month
    fin = (ciclo_fin.year, ciclo_fin.month)
    while (anio, mes) <= fin:
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        fecha_limite = date(anio, mes, min(dia_limite, ultimo_dia))
        periodos.append((anio, mes, fecha_limite))
        if mes == 12:
            anio, mes = anio + 1, 1
        else:
            mes += 1
    return periodos


def _fecha_limite_subperiodo(
    anio: int, mes: int, secuencia: int, cobros_por_mes: int, dia_limite: int
) -> date:
    """Fecha límite de cada sub-período del mes. Mensual usa `dia_limite`;
    quincenal/semanal reparten el mes en cortes proporcionales (la última
    secuencia cae el último día del mes)."""
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    if cobros_por_mes <= 1:
        return date(anio, mes, min(dia_limite, ultimo_dia))
    dia = min(round(ultimo_dia * secuencia / cobros_por_mes), ultimo_dia)
    return date(anio, mes, max(dia, 1))


def calcular_periodos(
    ciclo_inicio: date, ciclo_fin: date, dia_limite: int, cobros_por_mes: int
) -> list[tuple[int, int, int, date]]:
    """Devuelve [(anio, mes, secuencia, fecha_limite)] según la periodicidad.

    `cobros_por_mes` = 1 (mensual), 2 (quincenal), 4 (semanal). Cada mes del
    ciclo genera `cobros_por_mes` sub-períodos con secuencia 1..N.
    """
    cobros = max(1, cobros_por_mes)
    periodos: list[tuple[int, int, int, date]] = []
    anio, mes = ciclo_inicio.year, ciclo_inicio.month
    fin = (ciclo_fin.year, ciclo_fin.month)
    while (anio, mes) <= fin:
        for secuencia in range(1, cobros + 1):
            periodos.append(
                (
                    anio,
                    mes,
                    secuencia,
                    _fecha_limite_subperiodo(anio, mes, secuencia, cobros, dia_limite),
                )
            )
        if mes == 12:
            anio, mes = anio + 1, 1
        else:
            mes += 1
    return periodos
