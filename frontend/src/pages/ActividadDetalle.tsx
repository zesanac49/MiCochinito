import { type FormEvent, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Copy, Dices, Trophy } from 'lucide-react'
import { useAuth, rolActivo } from '@/store/auth'
import { usePeriodos, useParticipantes } from '@/hooks/data'
import {
  useAccionActividad,
  useActividad,
  useAsignarNumeros,
} from '@/hooks/actividades'
import { mensajeError } from '@/lib/api'
import { formatoCOP, nombrePeriodo } from '@/lib/formato'
import type { Actividad, NumeroActividad } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'
import { cn } from '@/lib/cn'

export function ActividadDetalle() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const { uuid = '' } = useParams()
  const actividad = useActividad(nat, uuid)
  const soloLectura = rolActivo() === 'CLIENTE'

  if (actividad.isLoading || !actividad.data) {
    return <p className="text-text-secondary">Cargando actividad…</p>
  }
  const a = actividad.data

  return (
    <div className="space-y-4">
      <Link to="/actividades" className="inline-flex items-center gap-1 text-sm text-text-secondary">
        <ArrowLeft size={16} /> Actividades
      </Link>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">{a.nombre}</h1>
          <Ayuda id="actividad_detalle" />
        </div>
        <Badge tono={a.estado === 'ABIERTA' ? 'acento' : 'neutro'}>{a.estado}</Badge>
      </div>

      {a.cantidad_numeros ? <GrillaNumeros a={a} nat={nat} uuid={uuid} soloLectura={soloLectura} /> : null}

      <Card>
        <div className="flex items-center justify-between">
          <span className="text-text-secondary">Premio (pozo) — se lo lleva el ganador</span>
          <span className="tabular text-lg font-bold text-warning">{formatoCOP(a.premio)}</span>
        </div>
        <div className="mt-2 flex items-center justify-between border-t border-text-secondary/10 pt-2">
          <span className="text-text-secondary">Utilidad proyectada (al fondo)</span>
          <span className="tabular text-2xl font-bold text-accent">{formatoCOP(a.utilidad)}</span>
        </div>
        {a.sorteo && (
          <p className="mt-2 flex items-center gap-2 text-sm">
            <Trophy size={16} className="text-warning" />
            {a.sorteo.hubo_ganador
              ? `Ganó el número ${a.sorteo.numero_ganador}`
              : `Sorteo sin ganador (número ${a.sorteo.numero_ganador})`}
          </p>
        )}
      </Card>

      {!soloLectura && <Acciones a={a} nat={nat} uuid={uuid} />}
    </div>
  )
}

function GrillaNumeros({
  a,
  nat,
  uuid,
  soloLectura,
}: {
  a: Actividad
  nat: string
  uuid: string
  soloLectura: boolean
}) {
  const pagar = useAccionActividad(nat, uuid, 'numeros/pagos')
  const porNumero = new Map<number, NumeroActividad>(a.numeros.map((n) => [n.numero, n]))
  const total = a.cantidad_numeros ?? 0
  const ganador = a.sorteo?.hubo_ganador ? a.sorteo.numero_ganador : null

  return (
    <Card well>
      <CardTitulo>Números</CardTitulo>
      <div className="grid grid-cols-6 gap-3 sm:grid-cols-10">
        {Array.from({ length: total }, (_, i) => i + 1).map((num) => {
          const n = porNumero.get(num)
          const asignado = !!n
          const pagado = n?.pagado ?? false
          const esGanador = ganador === num
          const puedePagar = !soloLectura && asignado && !pagado && a.estado === 'ABIERTA'
          return (
            <button
              key={num}
              type="button"
              disabled={!puedePagar || pagar.isPending}
              onClick={() => puedePagar && pagar.mutate({ numeros: [num] })}
              title={asignado ? (pagado ? 'Pagado' : 'Sin pago') : 'Libre'}
              className={cn(
                'flex h-11 w-11 items-center justify-center rounded-full text-sm font-semibold tabular transition-nm',
                !asignado && 'text-text-secondary/40 shadow-nm-well',
                asignado && !pagado && 'text-text-secondary opacity-50 shadow-nm-sm',
                pagado && 'text-accent shadow-nm-in ring-2 ring-accent',
                esGanador && 'ring-4 ring-warning',
                puedePagar && 'cursor-pointer hover:opacity-100',
              )}
            >
              {num}
            </button>
          )
        })}
      </div>
      <p className="mt-3 text-xs text-text-secondary">
        Pagado (con anillo) participa en el sorteo · sin pago queda inactivo (INV-07).
      </p>
    </Card>
  )
}

function Acciones({ a, nat, uuid }: { a: Actividad; nat: string; uuid: string }) {
  const participantes = useParticipantes(nat)
  const periodos = usePeriodos(nat)
  const asignar = useAsignarNumeros(nat, uuid)
  const abrir = useAccionActividad(nat, uuid, 'apertura')
  const movimiento = useAccionActividad(nat, uuid, 'movimientos')
  const sortear = useAccionActividad(nat, uuid, 'sorteo')
  const cerrar = useAccionActividad(nat, uuid, 'cierre')
  const clonar = useAccionActividad(nat, uuid, 'clonacion')

  const [asig, setAsig] = useState({ numero: '', participante_uuid: '' })
  const [mov, setMov] = useState({ tipo: 'GASTO', concepto: '', valor: '' })
  const [sorteo, setSorteo] = useState({ numero_ganador: '', fuente: '' })
  const [periodoClon, setPeriodoClon] = useState('')

  const editable = a.estado === 'BORRADOR' || a.estado === 'ABIERTA'

  function onAsignar(e: FormEvent) {
    e.preventDefault()
    asignar.mutate(
      { asignaciones: [{ numero: Number(asig.numero), participante_uuid: asig.participante_uuid }] },
      { onSuccess: () => setAsig({ numero: '', participante_uuid: '' }) },
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {editable && a.cantidad_numeros ? (
        <Card>
          <CardTitulo>Asignar número</CardTitulo>
          <form onSubmit={onAsignar} className="flex items-end gap-2">
            <Field
              label="Número"
              type="number"
              className="w-24"
              value={asig.numero}
              onChange={(e) => setAsig({ ...asig, numero: e.target.value })}
              required
            />
            <SelectField
              label="Participante"
              value={asig.participante_uuid}
              onChange={(e) => setAsig({ ...asig, participante_uuid: e.target.value })}
              required
            >
              <option value="">Selecciona…</option>
              {participantes.data?.map((p) => (
                <option key={p.uuid} value={p.uuid}>
                  {p.nombre}
                </option>
              ))}
            </SelectField>
            <Button type="submit" cargando={asignar.isPending}>
              Asignar
            </Button>
          </form>
          {a.estado === 'BORRADOR' && (
            <Button
              variante="primaria"
              className="mt-3"
              cargando={abrir.isPending}
              onClick={() => abrir.mutate(undefined)}
            >
              Abrir actividad
            </Button>
          )}
        </Card>
      ) : null}

      {a.estado === 'ABIERTA' && (
        <>
          <Card>
            <CardTitulo>Registrar movimiento</CardTitulo>
            <div className="grid grid-cols-2 gap-2">
              <SelectField
                label="Tipo"
                value={mov.tipo}
                onChange={(e) => setMov({ ...mov, tipo: e.target.value })}
              >
                <option value="INGRESO">Ingreso</option>
                <option value="GASTO">Gasto</option>
              </SelectField>
              <Field
                label="Valor"
                inputMode="decimal"
                value={mov.valor}
                onChange={(e) => setMov({ ...mov, valor: e.target.value })}
              />
              <div className="col-span-2">
                <Field
                  label="Concepto"
                  value={mov.concepto}
                  onChange={(e) => setMov({ ...mov, concepto: e.target.value })}
                />
              </div>
            </div>
            <Button
              className="mt-3"
              cargando={movimiento.isPending}
              disabled={!mov.concepto || !mov.valor}
              onClick={() =>
                movimiento.mutate(
                  { tipo: mov.tipo, concepto: mov.concepto, valor: mov.valor },
                  { onSuccess: () => setMov({ tipo: 'GASTO', concepto: '', valor: '' }) },
                )
              }
            >
              Registrar
            </Button>
          </Card>

          <Card>
            <CardTitulo>Sorteo</CardTitulo>
            <div className="flex items-end gap-2">
              <Field
                label="Número ganador"
                type="number"
                className="w-32"
                value={sorteo.numero_ganador}
                onChange={(e) => setSorteo({ ...sorteo, numero_ganador: e.target.value })}
              />
              <Field
                label="Fuente"
                value={sorteo.fuente}
                onChange={(e) => setSorteo({ ...sorteo, fuente: e.target.value })}
              />
              <Button
                variante="primaria"
                cargando={sortear.isPending}
                disabled={!sorteo.numero_ganador || !sorteo.fuente}
                onClick={() => {
                  if (
                    confirm(
                      `¿Registrar el número ${sorteo.numero_ganador} como ganador? El sorteo no se puede repetir.`,
                    )
                  )
                    sortear.mutate({
                      numero_ganador: Number(sorteo.numero_ganador),
                      fuente: sorteo.fuente,
                    })
                }}
              >
                <Dices size={16} /> Sortear
              </Button>
            </div>
            {sortear.isError && <p className="mt-2 text-sm text-danger">{mensajeError(sortear.error)}</p>}
          </Card>
        </>
      )}

      {(a.estado === 'ABIERTA' || a.estado === 'SORTEADA') && (
        <Card>
          <CardTitulo>Cerrar actividad</CardTitulo>
          <p className="mb-3 text-sm text-text-secondary">
            Traslada la utilidad ({formatoCOP(a.utilidad)}) al Fondo de Rentabilidad.
          </p>
          <Button
            variante="primaria"
            cargando={cerrar.isPending}
            onClick={() => {
              if (
                confirm(
                  `¿Cerrar la actividad? Traslada la utilidad (${formatoCOP(a.utilidad)}) al Fondo de Rentabilidad y no se puede reabrir.`,
                )
              )
                cerrar.mutate(undefined)
            }}
          >
            Cerrar
          </Button>
          {cerrar.isError && <p className="mt-2 text-sm text-danger">{mensajeError(cerrar.error)}</p>}
        </Card>
      )}

      <Card>
        <CardTitulo>Clonar al siguiente período</CardTitulo>
        <div className="flex items-end gap-2">
          <SelectField
            label="Período destino"
            value={periodoClon}
            onChange={(e) => setPeriodoClon(e.target.value)}
          >
            <option value="">Selecciona…</option>
            {periodos.data?.map((p) => (
              <option key={p.uuid} value={p.uuid}>
                {nombrePeriodo(p.anio, p.mes)}
              </option>
            ))}
          </SelectField>
          <Button
            cargando={clonar.isPending}
            disabled={!periodoClon}
            onClick={() => clonar.mutate({ periodo_destino_uuid: periodoClon })}
          >
            <Copy size={16} /> Clonar
          </Button>
        </div>
      </Card>
    </div>
  )
}
