import { FileSpreadsheet } from 'lucide-react'
import { Ayuda } from '@/components/ui/Ayuda'
import { useAuth } from '@/store/auth'
import { useDashboard } from '@/hooks/liquidacion'
import { formatoCOP } from '@/lib/formato'
import { exportarExcel } from '@/lib/exportar'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'

const NOMBRE_FUENTE: Record<string, string> = {
  INTERES_PAGADO: 'Intereses',
  UTILIDAD_ACTIVIDAD: 'Actividades',
  MULTA_PAGADA: 'Multas',
}

export function Reportes() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const dashboard = useDashboard(nat)
  const d = dashboard.data

  function exportar() {
    if (!d) return
    const filas = Object.entries(d.rentabilidad_por_fuente).map(([fuente, monto]) => ({
      Fuente: NOMBRE_FUENTE[fuente] ?? fuente,
      Monto: monto,
    }))
    exportarExcel('rentabilidad-por-fuente', filas)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">Reportes</h1>
          <Ayuda id="reportes" />
        </div>
        <Button onClick={exportar} disabled={!d}>
          <FileSpreadsheet size={16} /> Exportar Excel
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {d?.fondos.map((f) => (
          <Card key={f.tipo}>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-text-secondary">
                Fondo de {f.tipo === 'AHORRO' ? 'Ahorro' : 'Rentabilidad'}
              </span>
              <Badge tono={f.tipo === 'AHORRO' ? 'acento' : 'neutro'}>{f.tipo}</Badge>
            </div>
            <p className="tabular text-3xl font-bold">{formatoCOP(f.saldo)}</p>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitulo>Rentabilidad por fuente (RF-901)</CardTitulo>
        <ul className="space-y-2">
          {d &&
            Object.entries(d.rentabilidad_por_fuente).map(([fuente, monto]) => (
              <li key={fuente} className="flex items-center justify-between border-b border-white/40 py-2 last:border-0">
                <span>{NOMBRE_FUENTE[fuente] ?? fuente}</span>
                <span className="tabular font-semibold">{formatoCOP(monto)}</span>
              </li>
            ))}
        </ul>
        <p className="mt-2 text-xs text-text-secondary">
          La apertura por fuente jamás incluye retorno de capital (RN-034).
        </p>
      </Card>
    </div>
  )
}
