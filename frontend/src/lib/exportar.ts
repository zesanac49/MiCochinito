// Generación de acta PDF (jspdf) y export a Excel (xlsx) desde datos de la API.
// Todo el cálculo lo hace el backend; aquí solo se formatea para mostrar/exportar.
import { jsPDF } from 'jspdf'
import * as XLSX from 'xlsx'
import type { DetalleLiquidacion } from '@/types'
import { formatoCOP } from './formato'

export function exportarActaPDF(nombreNatillera: string, detalles: DetalleLiquidacion[]): void {
  const doc = new jsPDF()
  doc.setFontSize(16)
  doc.text(`Acta de liquidación — ${nombreNatillera}`, 14, 18)
  doc.setFontSize(9)
  let y = 30
  const cols: [string, number][] = [
    ['Participante', 14],
    ['Ahorros', 80],
    ['Rentabilidad', 115],
    ['Saldo final', 160],
  ]
  cols.forEach(([t, x]) => doc.text(t, x, y))
  y += 6
  for (const d of detalles) {
    doc.text(d.participante_nombre.slice(0, 30), 14, y)
    doc.text(formatoCOP(d.ahorros), 80, y)
    doc.text(formatoCOP(d.participacion_rentabilidad), 115, y)
    doc.text(formatoCOP(d.saldo_final), 160, y)
    y += 6
    if (y > 280) {
      doc.addPage()
      y = 20
    }
  }
  doc.save(`acta-${nombreNatillera}.pdf`)
}

export function exportarExcel(
  nombre: string,
  filas: Record<string, string | number>[],
): void {
  const hoja = XLSX.utils.json_to_sheet(filas)
  const libro = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(libro, hoja, 'Datos')
  XLSX.writeFile(libro, `${nombre}.xlsx`)
}
