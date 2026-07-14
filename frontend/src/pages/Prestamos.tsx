import { type FormEvent, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { AlarmClock, HandCoins } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { useParticipantes } from '@/hooks/data'
import {
  type NuevoPrestamo,
  useAprobarPrestamo,
  useDesembolsar,
  useDetectarMora,
  usePagarPrestamo,
  usePrestamos,
  useSolicitarPrestamo,
} from '@/hooks/prestamos'
import { mensajeError } from '@/lib/api'
import { formatoCOP } from '@/lib/formato'
import type { EstadoPrestamo, Prestamo } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'

const TONO: Record<EstadoPrestamo, 'acento' | 'neutro' | 'peligro' | 'alerta'> = {
  SOLICITADO: 'neutro',
  APROBADO: 'acento',
  DESEMBOLSADO: 'acento',
  EN_PAGO: 'acento',
  EN_MORA: 'peligro',
  PAGADO: 'neutro',
  RECHAZADO: 'peligro',
}

const VACIO: NuevoPrestamo = {
  participante_uuid: '',
  capital: '',
  tasa: '2.0',
  plazo_meses: 12,
}

export function Prestamos() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const participantes = useParticipantes(nat)
  const prestamos = usePrestamos(nat)
  const solicitar = useSolicitarPrestamo(nat)
  const mora = useDetectarMora(nat)
  const [form, setForm] = useState<NuevoPrestamo>(VACIO)

  function onSolicitar(e: FormEvent) {
    e.preventDefault()
    solicitar.mutate(form, { onSuccess: () => setForm({ ...VACIO }) })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">Préstamos</h1>
          <Ayuda id="prestamos" />
        </div>
        <Button cargando={mora.isPending} onClick={() => mora.mutate()}>
          <AlarmClock size={16} /> Detectar mora
        </Button>
      </div>

      <Card>
        <CardTitulo>Solicitar préstamo</CardTitulo>
        <form onSubmit={onSolicitar} className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Participante"
            value={form.participante_uuid}
            onChange={(e) => setForm({ ...form, participante_uuid: e.target.value })}
            required
          >
            <option value="">Selecciona…</option>
            {participantes.data?.map((p) => (
              <option key={p.uuid} value={p.uuid}>
                {p.nombre}
              </option>
            ))}
          </SelectField>
          <Field
            label="Capital"
            inputMode="decimal"
            value={form.capital}
            onChange={(e) => setForm({ ...form, capital: e.target.value })}
            required
          />
          <Field
            label="Tasa mensual (%)"
            inputMode="decimal"
            value={form.tasa}
            onChange={(e) => setForm({ ...form, tasa: e.target.value })}
            required
          />
          <Field
            label="Plazo (meses)"
            type="number"
            min={1}
            max={120}
            value={form.plazo_meses}
            onChange={(e) => setForm({ ...form, plazo_meses: Number(e.target.value) })}
            required
          />
          <div className="sm:col-span-2 flex items-center justify-between">
            {solicitar.isError ? (
              <p className="text-sm text-danger">{mensajeError(solicitar.error)}</p>
            ) : (
              <span />
            )}
            <Button type="submit" variante="primaria" cargando={solicitar.isPending}>
              <HandCoins size={16} /> Solicitar
            </Button>
          </div>
        </form>
      </Card>

      <div className="space-y-3">
        {prestamos.data?.map((p) => (
          <PrestamoCard key={p.uuid} prestamo={p} nat={nat} />
        ))}
        {prestamos.data?.length === 0 && (
          <p className="text-sm text-text-secondary">Aún no hay préstamos.</p>
        )}
      </div>
    </div>
  )
}

function PrestamoCard({ prestamo: p, nat }: { prestamo: Prestamo; nat: string }) {
  const aprobar = useAprobarPrestamo(nat)
  const desembolsar = useDesembolsar(nat)
  const pagar = usePagarPrestamo(nat)
  const [monto, setMonto] = useState('')

  const enCurso = aprobar.isPending || desembolsar.isPending || pagar.isPending

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="tabular text-lg font-bold">{formatoCOP(p.capital)}</span>
            <Badge tono={TONO[p.estado]}>{p.estado}</Badge>
          </div>
          <p className="text-xs text-text-secondary">
            Tasa {p.tasa}% · plazo {p.plazo_meses}m · saldo{' '}
            <span className="tabular">{formatoCOP(p.saldo_capital)}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {p.estado === 'SOLICITADO' && (
            <>
              <Button
                variante="primaria"
                cargando={enCurso}
                onClick={() => aprobar.mutate({ uuid: p.uuid, body: { aprobar: true } })}
              >
                Aprobar
              </Button>
              <Button
                variante="peligro"
                onClick={() => {
                  const motivo = prompt('Motivo del rechazo del préstamo:')?.trim()
                  if (motivo) aprobar.mutate({ uuid: p.uuid, body: { aprobar: false, motivo } })
                }}
              >
                Rechazar
              </Button>
            </>
          )}
          {p.estado === 'APROBADO' && (
            <Button
              variante="primaria"
              cargando={enCurso}
              onClick={() => {
                if (
                  confirm(
                    `¿Desembolsar ${formatoCOP(p.capital)}? Sale del Fondo de Ahorro y queda registrado en el ledger.`,
                  )
                )
                  desembolsar.mutate({ uuid: p.uuid })
              }}
            >
              Desembolsar
            </Button>
          )}
          {(p.estado === 'EN_PAGO' || p.estado === 'EN_MORA') && (
            <div className="flex items-end gap-2">
              <Field
                label="Abono"
                inputMode="decimal"
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                className="w-32"
              />
              <Button
                variante="primaria"
                cargando={enCurso}
                disabled={!monto}
                onClick={() =>
                  pagar.mutate({ uuid: p.uuid, body: { monto } }, { onSuccess: () => setMonto('') })
                }
              >
                Pagar
              </Button>
            </div>
          )}
        </div>
      </div>
      {(aprobar.isError || desembolsar.isError || pagar.isError) && (
        <p className="mt-2 text-sm text-danger">
          {mensajeError(aprobar.error ?? desembolsar.error ?? pagar.error)}
        </p>
      )}
      {p.motivo_rechazo && (
        <p className="mt-1 text-xs text-text-secondary">Motivo: {p.motivo_rechazo}</p>
      )}
    </Card>
  )
}
