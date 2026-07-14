import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Ayuda } from '@/components/ui/Ayuda'
import { UserPlus } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { type NuevoParticipante, useCrearParticipante, useParticipantes } from '@/hooks/data'
import { mensajeError } from '@/lib/api'
import type { TipoDocumento } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'
import { Tabla, Td, Th, Tr } from '@/components/ui/Table'

const VACIO: NuevoParticipante = {
  nombre: '',
  tipo_documento: 'CC',
  numero_documento: '',
  fecha_ingreso: new Date().toISOString().slice(0, 10),
  telefono: '',
}

const TONO_ESTADO = {
  ACTIVO: 'acento',
  SUSPENDIDO: 'alerta',
  RETIRADO: 'neutro',
} as const

export function Participantes() {
  const nat = useAuth((s) => s.natilleraUuid)
  const lista = useParticipantes(nat)
  const crear = useCrearParticipante(nat ?? '')
  const [form, setForm] = useState<NuevoParticipante>(VACIO)

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nat) return
    crear.mutate(form, { onSuccess: () => setForm(VACIO) })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Participantes</h1>
        <Ayuda id="participantes" />
      </div>

      <Card>
        <CardTitulo>Inscribir participante</CardTitulo>
        <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Nombre"
            value={form.nombre}
            onChange={(e) => setForm({ ...form, nombre: e.target.value })}
            required
          />
          <div className="grid grid-cols-3 gap-2">
            <SelectField
              label="Tipo"
              value={form.tipo_documento}
              onChange={(e) =>
                setForm({ ...form, tipo_documento: e.target.value as TipoDocumento })
              }
            >
              {(['CC', 'CE', 'TI', 'PP'] as const).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </SelectField>
            <div className="col-span-2">
              <Field
                label="Documento"
                value={form.numero_documento}
                onChange={(e) => setForm({ ...form, numero_documento: e.target.value })}
                required
              />
            </div>
          </div>
          <Field
            label="Fecha de ingreso"
            type="date"
            value={form.fecha_ingreso}
            onChange={(e) => setForm({ ...form, fecha_ingreso: e.target.value })}
            required
          />
          <Field
            label="Teléfono"
            value={form.telefono ?? ''}
            onChange={(e) => setForm({ ...form, telefono: e.target.value })}
          />
          <div className="sm:col-span-2 flex items-center justify-between">
            {crear.isError ? (
              <p className="text-sm text-danger">{mensajeError(crear.error)}</p>
            ) : (
              <span />
            )}
            <Button type="submit" variante="primaria" cargando={crear.isPending}>
              <UserPlus size={16} /> Inscribir
            </Button>
          </div>
        </form>
      </Card>

      <Card well>
        <CardTitulo>Inscritos ({lista.data?.length ?? 0})</CardTitulo>
        <Tabla>
          <thead>
            <tr>
              <Th>Nombre</Th>
              <Th>Documento</Th>
              <Th>Estado</Th>
            </tr>
          </thead>
          <tbody>
            {lista.data?.map((p) => (
              <Tr key={p.uuid}>
                <Td>
                  <Link to={`/participantes/${p.uuid}`} className="font-medium text-accent hover:underline">
                    {p.nombre}
                  </Link>
                </Td>
                <Td tabular>
                  {p.tipo_documento} {p.numero_documento}
                </Td>
                <Td>
                  <Badge tono={TONO_ESTADO[p.estado]}>{p.estado}</Badge>
                </Td>
              </Tr>
            ))}
          </tbody>
        </Tabla>
        {lista.data?.length === 0 && (
          <p className="mt-3 text-sm text-text-secondary">Aún no hay participantes.</p>
        )}
      </Card>
    </div>
  )
}
