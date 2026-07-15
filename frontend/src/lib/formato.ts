// Formateo de montos es-CO (DIS-09). SOLO para mostrar: el string decimal de la
// API se convierte a número únicamente para formatear, nunca para operar
// (la aritmética de dinero la hace la API, doc 08 §4).

const cop = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

export function formatoCOP(montoStr: string): string {
  const n = Number(montoStr)
  if (Number.isNaN(n)) return montoStr
  return cop.format(n)
}

const MESES = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
  'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

export function nombrePeriodo(anio: number, mes: number): string {
  return `${MESES[mes - 1] ?? mes} ${anio}`
}

// Sufijo de sub-período según la periodicidad (quincenal/semanal). Mensual: vacío.
export function sufijoPeriodicidad(secuencia: number, periodicidad?: string | null): string {
  if (!periodicidad || periodicidad === 'MENSUAL') return ''
  if (periodicidad === 'QUINCENAL') return ` · ${secuencia === 1 ? '1ª' : '2ª'} quincena`
  if (periodicidad === 'SEMANAL') return ` · semana ${secuencia}`
  return ` · ${secuencia}`
}

// Cobros por mes según la periodicidad (espeja backend: Periodicidad.cobros_por_mes()).
export function cobrosPorMes(periodicidad?: string | null): number {
  if (periodicidad === 'QUINCENAL') return 2
  if (periodicidad === 'SEMANAL') return 4
  return 1 // MENSUAL o desconocido
}

// Cuota efectiva de UN período = cuota mensual ÷ cobros del mes.
// Se calcula en centavos enteros con redondeo "half up" para reflejar EXACTO lo que
// cobra el backend (Dinero.dividir_entre) y no operar dinero en flotante (TEC-01).
export function cuotaPorPeriodo(mensualStr: string, cobros: number): string {
  const centavos = Math.round(Number(mensualStr) * 100)
  if (!Number.isFinite(centavos) || cobros <= 0) return mensualStr
  return centavosADecimal(Math.round(centavos / cobros))
}

// Suma una lista de montos (strings decimales) en centavos enteros → string decimal.
export function sumarMontos(montos: string[]): string {
  const centavos = montos.reduce((acc, m) => acc + Math.round(Number(m) * 100), 0)
  return centavosADecimal(centavos)
}

function centavosADecimal(centavos: number): string {
  const pesos = Math.trunc(centavos / 100)
  const resto = Math.abs(centavos % 100)
  return `${pesos}.${String(resto).padStart(2, '0')}`
}
