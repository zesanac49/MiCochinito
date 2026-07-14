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
    """Devuelve [(anio, mes, fecha_limite_cuota)] para cada mes del ciclo."""
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
