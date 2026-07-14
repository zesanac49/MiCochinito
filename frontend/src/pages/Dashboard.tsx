import { useAuth } from '@/store/auth'
import { Ayuda } from '@/components/ui/Ayuda'
import { useFondos } from '@/hooks/data'
import { formatoCOP } from '@/lib/formato'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'

export function Dashboard() {
  const nat = useAuth((s) => s.natilleraUuid)
  const fondos = useFondos(nat)

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Resumen</h1>
        <Ayuda id="resumen" />
      </div>
      {fondos.isLoading && <p className="text-text-secondary">Cargando saldos…</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {fondos.data?.map((f) => (
          <Card key={f.tipo}>
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-text-secondary">
                Fondo de {f.tipo === 'AHORRO' ? 'Ahorro' : 'Rentabilidad'}
              </span>
              <Badge tono={f.tipo === 'AHORRO' ? 'acento' : 'neutro'}>{f.tipo}</Badge>
            </div>
            <p className="tabular text-3xl font-bold text-text-primary">
              {formatoCOP(f.saldo)}
            </p>
          </Card>
        ))}
      </div>
    </div>
  )
}
