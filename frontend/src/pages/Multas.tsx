import { type FormEvent, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { Ban, ScrollText } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { useParticipantes } from '@/hooks/data'
import {
  useAnularMulta,
  useCatalogo,
  useCrearCatalogo,
  useImponerMulta,
  useMultas,
  usePagarMulta,
} from '@/hooks/multas'
import { mensajeError } from '@/lib/api'
import { formatoCOP } from '@/lib/formato'
import type { EstadoMulta, Multa } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'

const TIPOS = ['MORA_CUOTA', 'MORA_PRESTAMO', 'MORA_ACTIVIDAD', 'OTRA']
const TONO: Record<EstadoMulta, 'acento' | 'alerta' | 'neutro'> = {
  IMPUESTA: 'alerta',
  PAGADA: 'acento',
  ANULADA: 'neutro',
}

export function Multas() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const participantes = useParticipantes(nat)
  const catalogo = useCatalogo(nat)
  const crearCat = useCrearCatalogo(nat)
  const multas = useMultas(nat)
  const imponer = useImponerMulta(nat)

  const [cat, setCat] = useState({ nombre: '', tipo: 'MORA_CUOTA', valor: '' })
  const [multa, setMulta] = useState({ participante_uuid: '', motivo: '', catalogo_uuid: '' })

  function onCrearCat(e: FormEvent) {
    e.preventDefault()
    crearCat.mutate(cat, { onSuccess: () => setCat({ nombre: '', tipo: 'MORA_CUOTA', valor: '' }) })
  }

  function onImponer(e: FormEvent) {
    e.preventDefault()
    imponer.mutate(
      {
        participante_uuid: multa.participante_uuid,
        motivo: multa.motivo,
        catalogo_uuid: multa.catalogo_uuid || undefined,
      },
      { onSuccess: () => setMulta({ participante_uuid: '', motivo: '', catalogo_uuid: '' }) },
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Multas</h1>
        <Ayuda id="multas" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardTitulo>Catálogo de multas</CardTitulo>
          <form onSubmit={onCrearCat} className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <Field
                label="Nombre"
                value={cat.nombre}
                onChange={(e) => setCat({ ...cat, nombre: e.target.value })}
                required
              />
            </div>
            <SelectField
              label="Tipo"
              value={cat.tipo}
              onChange={(e) => setCat({ ...cat, tipo: e.target.value })}
            >
              {TIPOS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </SelectField>
            <Field
              label="Valor"
              inputMode="decimal"
              value={cat.valor}
              onChange={(e) => setCat({ ...cat, valor: e.target.value })}
              required
            />
            <div className="col-span-2 flex justify-end">
              <Button type="submit" cargando={crearCat.isPending}>
                <ScrollText size={16} /> Agregar
              </Button>
            </div>
          </form>
          <ul className="mt-3 space-y-1 text-sm">
            {catalogo.data?.map((c) => (
              <li key={c.uuid} className="flex justify-between">
                <span>{c.nombre}</span>
                <span className="tabular text-text-secondary">{formatoCOP(c.valor)}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitulo>Imponer multa</CardTitulo>
          <form onSubmit={onImponer} className="space-y-3">
            <SelectField
              label="Participante"
              value={multa.participante_uuid}
              onChange={(e) => setMulta({ ...multa, participante_uuid: e.target.value })}
              required
            >
              <option value="">Selecciona…</option>
              {participantes.data?.map((p) => (
                <option key={p.uuid} value={p.uuid}>
                  {p.nombre}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Multa del catálogo"
              value={multa.catalogo_uuid}
              onChange={(e) => setMulta({ ...multa, catalogo_uuid: e.target.value })}
              required
            >
              <option value="">Selecciona…</option>
              {catalogo.data?.map((c) => (
                <option key={c.uuid} value={c.uuid}>
                  {c.nombre} · {formatoCOP(c.valor)}
                </option>
              ))}
            </SelectField>
            <Field
              label="Motivo"
              value={multa.motivo}
              onChange={(e) => setMulta({ ...multa, motivo: e.target.value })}
              required
            />
            {imponer.isError && <p className="text-sm text-danger">{mensajeError(imponer.error)}</p>}
            <div className="flex justify-end">
              <Button type="submit" variante="primaria" cargando={imponer.isPending}>
                Imponer
              </Button>
            </div>
          </form>
        </Card>
      </div>

      <Card>
        <CardTitulo>Multas ({multas.data?.length ?? 0})</CardTitulo>
        <div className="space-y-2">
          {multas.data?.map((m) => (
            <MultaFila key={m.uuid} multa={m} nat={nat} />
          ))}
          {multas.data?.length === 0 && (
            <p className="text-sm text-text-secondary">Sin multas registradas.</p>
          )}
        </div>
      </Card>
    </div>
  )
}

function MultaFila({ multa: m, nat }: { multa: Multa; nat: string }) {
  const pagar = usePagarMulta(nat)
  const anular = useAnularMulta(nat)
  const enCurso = pagar.isPending || anular.isPending

  return (
    <div className="flex items-center justify-between border-b border-white/40 py-2 last:border-0">
      <div>
        <div className="flex items-center gap-2">
          <span className="tabular font-medium">{formatoCOP(m.valor)}</span>
          <Badge tono={TONO[m.estado]}>{m.estado}</Badge>
        </div>
        <p className="text-xs text-text-secondary">{m.motivo}</p>
      </div>
      {m.estado === 'IMPUESTA' && (
        <div className="flex gap-2">
          <Button variante="primaria" cargando={enCurso} onClick={() => pagar.mutate({ uuid: m.uuid })}>
            Pagar
          </Button>
          <Button
            variante="peligro"
            cargando={enCurso}
            onClick={() => {
              const justificacion = prompt('¿Por qué se anula esta multa? (queda en la auditoría)')?.trim()
              if (justificacion) anular.mutate({ uuid: m.uuid, body: { justificacion } })
            }}
          >
            <Ban size={16} /> Anular
          </Button>
        </div>
      )}
    </div>
  )
}
