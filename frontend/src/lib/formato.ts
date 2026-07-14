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
