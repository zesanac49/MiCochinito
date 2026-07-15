import { useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, HandCoins, PiggyBank } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { usePeriodos } from '@/hooks/data'
import {
  useAporteExtraordinario,
  useCambiarEstadoParticipante,
  useCuenta,
  useFijarCuota,
  usePagarCuota,
  useParticipante,
} from '@/hooks/participante'
import { mensajeError } from '@/lib/api'
import { formatoCOP, nombrePeriodo } from '@/lib/formato'
import type { EstadoParticipante } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'
import { Tabla, Td, Th, Tr } from '@/components/ui/Table'

const ESTADOS: EstadoParticipante[] = ['ACTIVO', 'SUSPENDIDO', 'RETIRADO']
const TONO = { ACTIVO: 'acento', SUSPENDIDO: 'alerta', RETIRADO: 'neutro' } as const

export function ParticipanteDetalle() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const { uuid = '' } = useParams()
  const participante = useParticipante(nat, uuid)
  const cuenta = useCuenta(nat, uuid)
  const periodos = usePeriodos(nat)
  const cambiarEstado = useCambiarEstadoParticipante(nat, uuid)
  const aporte = useAporteExtraordinario(nat, uuid)
  const pagarCuota = usePagarCuota(nat, uuid)
  const fijarCuota = useFijarCuota(nat, uuid)

  const [montoAporte, setMontoAporte] = useState('')
  const [periodoCuota, setPeriodoCuota] = useState('')
  const [cuotaInput, setCuotaInput] = useState('')

  const p = participante.data
  const c = cuenta.data

  return (
    <div className="space-y-4">
      <Link to="/participantes" className="inline-flex items-center gap-1 text-sm text-text-secondary">
        <ArrowLeft size={16} /> Participantes
      </Link>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">{p?.nombre ?? 'Participante'}</h1>
          <Ayuda id="participante_detalle" />
        </div>
        {p && <Badge tono={TONO[p.estado]}>{p.estado}</Badge>}
      </div>

      {/* Saldos */}
      <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
        <Card>
          <p className="text-[11px] uppercase tracking-[0.06em] text-text-secondary">Ahorros</p>
          <p className="tabular text-2xl font-bold text-accent">{formatoCOP(c?.saldos.ahorros ?? '0')}</p>
        </Card>
        <Card>
          <p className="text-[11px] uppercase tracking-[0.06em] text-text-secondary">Intereses pend.</p>
          <p className="tabular text-2xl font-bold">{formatoCOP(c?.saldos.intereses_pendientes ?? '0')}</p>
        </Card>
        <Card>
          <p className="text-[11px] uppercase tracking-[0.06em] text-text-secondary">Multas pend.</p>
          <p className="tabular text-2xl font-bold">{formatoCOP(c?.saldos.multas_pendientes ?? '0')}</p>
        </Card>
        <Card>
          <p className="text-[11px] uppercase tracking-[0.06em] text-text-secondary">Mora pend.</p>
          <p className="tabular text-2xl font-bold text-warning">{formatoCOP(c?.saldos.mora_pendiente ?? '0')}</p>
        </Card>
      </div>

      {/* Cuota mensual propia */}
      <Card>
        <CardTitulo>Cuota mensual de esta persona</CardTitulo>
        <div className="flex items-end gap-2">
          <Field
            label="Valor de la cuota"
            inputMode="decimal"
            value={cuotaInput}
            onChange={(e) => setCuotaInput(e.target.value)}
            placeholder={p?.valor_cuota ?? 'Por defecto de la natillera'}
          />
          <Button
            variante="primaria"
            cargando={fijarCuota.isPending}
            disabled={!cuotaInput.trim()}
            onClick={() => fijarCuota.mutate(cuotaInput.trim(), { onSuccess: () => setCuotaInput('') })}
          >
            Guardar
          </Button>
        </div>
        <p className="mt-2 text-xs text-text-secondary">
          Actual:{' '}
          <strong>
            {p?.valor_cuota
              ? formatoCOP(p.valor_cuota)
              : 'usa el valor por defecto de la natillera'}
          </strong>
          . Con esta cuota se cobra el recaudo mensual de la persona.
        </p>
        {fijarCuota.isError && (
          <p className="mt-2 text-sm text-danger">{mensajeError(fijarCuota.error)}</p>
        )}
      </Card>

      {/* Acciones de ahorro */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitulo>Pagar cuota de un período</CardTitulo>
          <div className="flex items-end gap-2">
            <SelectField label="Período" value={periodoCuota} onChange={(e) => setPeriodoCuota(e.target.value)}>
              <option value="">Selecciona…</option>
              {periodos.data?.map((per) => (
                <option key={per.uuid} value={per.uuid}>
                  {nombrePeriodo(per.anio, per.mes)}
                </option>
              ))}
            </SelectField>
            <Button
              variante="primaria"
              cargando={pagarCuota.isPending}
              disabled={!periodoCuota}
              onClick={() => pagarCuota.mutate(periodoCuota, { onSuccess: () => setPeriodoCuota('') })}
            >
              <PiggyBank size={16} /> Pagar
            </Button>
          </div>
          {pagarCuota.isError && <p className="mt-2 text-sm text-danger">{mensajeError(pagarCuota.error)}</p>}
        </Card>

        <Card>
          <CardTitulo>Aporte extraordinario</CardTitulo>
          <div className="flex items-end gap-2">
            <Field label="Monto" inputMode="decimal" value={montoAporte} onChange={(e) => setMontoAporte(e.target.value)} />
            <Button
              cargando={aporte.isPending}
              disabled={!montoAporte}
              onClick={() => aporte.mutate(montoAporte, { onSuccess: () => setMontoAporte('') })}
            >
              <HandCoins size={16} /> Registrar
            </Button>
          </div>
          {aporte.isError && <p className="mt-2 text-sm text-danger">{mensajeError(aporte.error)}</p>}
        </Card>
      </div>

      {/* Cambiar estado */}
      <Card>
        <CardTitulo>Estado del participante</CardTitulo>
        <div className="flex gap-2">
          {ESTADOS.map((est) => (
            <Button
              key={est}
              variante={p?.estado === est ? 'primaria' : 'neutra'}
              disabled={p?.estado === est}
              cargando={cambiarEstado.isPending}
              onClick={() => cambiarEstado.mutate(est)}
            >
              {est}
            </Button>
          ))}
        </div>
        {cambiarEstado.isError && <p className="mt-2 text-sm text-danger">{mensajeError(cambiarEstado.error)}</p>}
      </Card>

      {/* Estado de cuenta (asientos) */}
      <Card well>
        <CardTitulo>Movimientos ({c?.asientos.length ?? 0})</CardTitulo>
        <Tabla>
          <thead>
            <tr>
              <Th>Concepto</Th>
              <Th>Fondo</Th>
              <Th right>Monto</Th>
            </tr>
          </thead>
          <tbody>
            {c?.asientos.map((a) => (
              <Tr key={a.uuid}>
                <Td>{a.concepto}</Td>
                <Td>{a.fondo}</Td>
                <Td right tabular>
                  {a.naturaleza === 'DEBITO' ? '−' : '+'} {formatoCOP(a.monto)}
                </Td>
              </Tr>
            ))}
          </tbody>
        </Tabla>
        {c?.asientos.length === 0 && (
          <p className="mt-3 text-sm text-text-secondary">Sin movimientos aún.</p>
        )}
      </Card>
    </div>
  )
}
