import { useMemo, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { CheckCircle2, PiggyBank } from 'lucide-react'
import { useAuth } from '@/store/auth'
import { usePagarLote, useParticipantes, usePeriodos } from '@/hooks/data'
import { useNatillera } from '@/hooks/natilleras'
import { mensajeError } from '@/lib/api'
import { formatoCOP, nombrePeriodo } from '@/lib/formato'
import type { Participante, ResumenLote } from '@/types'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { SelectField } from '@/components/ui/Field'
import { Toggle } from '@/components/ui/Toggle'

export function PagosLote() {
  const nat = useAuth((s) => s.natilleraUuid)
  const natillera = useNatillera(nat)
  const periodos = usePeriodos(nat)
  const participantes = useParticipantes(nat)
  const pagar = usePagarLote(nat ?? '')

  const [periodoUuid, setPeriodoUuid] = useState('')
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set())
  const [resumen, setResumen] = useState<ResumenLote | null>(null)

  // Cuota por defecto de la natillera; cada persona puede tener la suya.
  const cuotaDefault = natillera.data?.configuracion?.valor_cuota ?? null
  const cuotaDe = (p: Participante): string | null => p.valor_cuota ?? cuotaDefault
  const periodoNombre = periodos.data?.find((p) => p.uuid === periodoUuid)

  const activos = useMemo(
    () => (participantes.data ?? []).filter((p) => p.estado === 'ACTIVO'),
    [participantes.data],
  )

  // Total estimado = suma de las cuotas de los seleccionados (cada quien la suya).
  const totalEstimado =
    seleccion.size > 0
      ? String(
          activos
            .filter((p) => seleccion.has(p.uuid))
            .reduce((acc, p) => acc + Number(cuotaDe(p) ?? 0), 0),
        )
      : null

  function alternar(uuid: string) {
    setSeleccion((prev) => {
      const s = new Set(prev)
      if (s.has(uuid)) s.delete(uuid)
      else s.add(uuid)
      return s
    })
  }

  function confirmar() {
    if (!periodoUuid || seleccion.size === 0) return
    const items = [...seleccion].map((participante_uuid) => ({
      participante_uuid,
      periodo_uuid: periodoUuid,
    }))
    pagar.mutate(items, {
      onSuccess: (r) => {
        setResumen(r)
        setSeleccion(new Set())
      },
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">Recaudo de cuotas</h1>
          <Ayuda id="recaudo" />
        </div>
        <p className="text-sm text-text-secondary">
          Registra el pago de la <strong>cuota de ahorro</strong> de un período. Cada pago
          acredita al Fondo de Ahorro.
        </p>
      </div>

      {/* 1) Elegir período + mostrar el monto de la cuota. */}
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-[220px] flex-1">
            <SelectField
              label="Período a cobrar"
              value={periodoUuid}
              onChange={(e) => {
                setPeriodoUuid(e.target.value)
                setResumen(null)
              }}
            >
              <option value="">Selecciona un período…</option>
              {periodos.data?.map((p) => (
                <option key={p.uuid} value={p.uuid}>
                  {nombrePeriodo(p.anio, p.mes)}
                </option>
              ))}
            </SelectField>
          </div>
          {cuotaDefault && (
            <div className="flex items-center gap-2 rounded-nm-sm bg-surface px-4 py-2.5 shadow-nm-in">
              <PiggyBank size={18} className="text-accent" />
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-[0.06em] text-text-secondary">
                  Cuota por defecto
                </p>
                <p className="tabular font-bold text-accent">{formatoCOP(cuotaDefault)}</p>
              </div>
            </div>
          )}
        </div>
        {periodoNombre && (
          <p className="mt-2 text-xs text-text-secondary">
            Cobrando la cuota de <strong>{nombrePeriodo(periodoNombre.anio, periodoNombre.mes)}</strong>.
            Cada persona paga <strong>su propia cuota</strong>.
          </p>
        )}
      </Card>

      {/* 2) Marcar quién pagó. */}
      {periodoUuid && (
        <Card well>
          <CardTitulo>Marca quién pagó ({seleccion.size} seleccionados)</CardTitulo>
          <ul className="divide-y divide-white/40">
            {activos.map((p) => (
              <li key={p.uuid} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="font-medium">{p.nombre}</p>
                  <p className="tabular text-xs text-text-secondary">
                    {p.tipo_documento} {p.numero_documento}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="tabular text-sm font-semibold text-accent">
                    {cuotaDe(p) ? formatoCOP(cuotaDe(p)!) : '—'}
                  </span>
                  <Toggle
                    activo={seleccion.has(p.uuid)}
                    onChange={() => alternar(p.uuid)}
                    etiqueta={`Marcar pago de ${p.nombre}`}
                  />
                </div>
              </li>
            ))}
          </ul>
          {activos.length === 0 && (
            <p className="text-sm text-text-secondary">No hay participantes activos.</p>
          )}
        </Card>
      )}

      {/* 3) Confirmar (barra fija en móvil). */}
      {periodoUuid && activos.length > 0 && (
        <div className="sticky bottom-4 z-10">
          <Card className="flex items-center justify-between !p-4">
            <div>
              <p className="text-sm text-text-secondary">
                {seleccion.size} pago(s) por registrar
              </p>
              {totalEstimado && (
                <p className="tabular text-lg font-bold">
                  Total ≈ {formatoCOP(totalEstimado)}
                </p>
              )}
            </div>
            <Button
              variante="primaria"
              disabled={seleccion.size === 0}
              cargando={pagar.isPending}
              onClick={confirmar}
            >
              <CheckCircle2 size={16} /> Registrar
            </Button>
          </Card>
        </div>
      )}

      {pagar.isError && <p className="text-sm text-danger">{mensajeError(pagar.error)}</p>}

      {/* Resumen de control tras confirmar. */}
      {resumen && (
        <Card>
          <CardTitulo>Resumen de recaudo</CardTitulo>
          <div className="mb-3 flex items-baseline justify-between">
            <span className="text-text-secondary">
              {resumen.cantidad_pagados} pago(s) registrados
            </span>
            <span className="tabular text-2xl font-bold text-accent">
              {formatoCOP(resumen.total_recaudado)}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {resumen.items
              .filter((i) => i.estado !== 'PAGADO')
              .map((i) => (
                <Badge key={i.participante_uuid} tono="alerta">
                  {i.estado === 'YA_PAGADO' ? 'Ya estaba pagado' : 'No encontrado'}
                </Badge>
              ))}
          </div>
        </Card>
      )}
    </div>
  )
}
