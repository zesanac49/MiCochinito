import { type FormEvent, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { Link } from 'react-router-dom'
import { Dices, Plus } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { usePeriodos } from '@/hooks/data'
import { type NuevaActividad, useActividades, useCrearActividad } from '@/hooks/actividades'
import { mensajeError } from '@/lib/api'
import { formatoCOP, nombrePeriodo } from '@/lib/formato'
import type { EstadoActividad, TipoActividad } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'

const TIPOS: TipoActividad[] = ['POLLA', 'RIFA', 'BINGO', 'BAZAR', 'VENTA', 'OTRO']
const TONO: Record<EstadoActividad, 'neutro' | 'acento' | 'alerta'> = {
  BORRADOR: 'neutro',
  ABIERTA: 'acento',
  SORTEADA: 'alerta',
  CERRADA: 'neutro',
}

export function Actividades() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const periodos = usePeriodos(nat)
  const actividades = useActividades(nat)
  const crear = useCrearActividad(nat)

  const [form, setForm] = useState<NuevaActividad>({
    tipo: 'POLLA',
    nombre: '',
    periodo_uuid: '',
    valor_numero: '',
    cantidad_numeros: 20,
    premio: '',
  })

  function onCrear(e: FormEvent) {
    e.preventDefault()
    const payload: NuevaActividad =
      form.tipo === 'POLLA'
        ? form
        : { tipo: form.tipo, nombre: form.nombre, periodo_uuid: form.periodo_uuid }
    crear.mutate(payload, {
      onSuccess: () => setForm({ ...form, nombre: '', valor_numero: '', premio: '' }),
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Actividades</h1>
        <Ayuda id="actividades" />
      </div>

      <Card>
        <CardTitulo>Nueva actividad</CardTitulo>
        <form onSubmit={onCrear} className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Tipo"
            value={form.tipo}
            onChange={(e) => setForm({ ...form, tipo: e.target.value as TipoActividad })}
          >
            {TIPOS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </SelectField>
          <Field
            label="Nombre"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            required
          />
          <SelectField
            label="Período"
            value={form.periodo_uuid}
            onChange={(e) => setForm({ ...form, periodo_uuid: e.target.value })}
            required
          >
            <option value="">Selecciona…</option>
            {periodos.data?.map((p) => (
              <option key={p.uuid} value={p.uuid}>
                {nombrePeriodo(p.anio, p.mes)}
              </option>
            ))}
          </SelectField>
          {form.tipo === 'POLLA' && (
            <>
              <Field
                label="Valor por número"
                inputMode="decimal"
                value={form.valor_numero ?? ''}
                onChange={(e) => setForm({ ...form, valor_numero: e.target.value })}
              />
              <Field
                label="Cantidad de números"
                type="number"
                min={1}
                max={1000}
                value={form.cantidad_numeros ?? 20}
                onChange={(e) => setForm({ ...form, cantidad_numeros: Number(e.target.value) })}
              />
              <Field
                label="Premio"
                inputMode="decimal"
                value={form.premio ?? ''}
                onChange={(e) => setForm({ ...form, premio: e.target.value })}
              />
            </>
          )}
          <div className="sm:col-span-2 flex items-center justify-between">
            {crear.isError ? (
              <p className="text-sm text-danger">{mensajeError(crear.error)}</p>
            ) : (
              <span />
            )}
            <Button type="submit" variante="primaria" cargando={crear.isPending}>
              <Plus size={16} /> Crear
            </Button>
          </div>
        </form>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2">
        {actividades.data?.map((a) => (
          <Link key={a.uuid} to={`/actividades/${a.uuid}`}>
            <Card className="transition-nm hover:brightness-[1.02]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Dices size={18} className="text-accent" />
                  <span className="font-semibold">{a.nombre}</span>
                </div>
                <Badge tono={TONO[a.estado]}>{a.estado}</Badge>
              </div>
              <p className="mt-1 text-xs text-text-secondary">
                {a.tipo} · utilidad <span className="tabular">{formatoCOP(a.utilidad)}</span>
              </p>
            </Card>
          </Link>
        ))}
        {actividades.data?.length === 0 && (
          <p className="text-sm text-text-secondary">Aún no hay actividades.</p>
        )}
      </div>
    </div>
  )
}
