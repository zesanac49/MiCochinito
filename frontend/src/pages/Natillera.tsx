import { type FormEvent, useEffect, useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { Building2, PlusCircle, Save, StepForward } from 'lucide-react'
import { useAuth } from '@/store/auth'
import {
  type Configuracion,
  type NuevaNatillera,
  useConfigurar,
  useCrearNatillera,
  useNatillera,
  useTransicionar,
} from '@/hooks/natilleras'
import { mensajeError } from '@/lib/api'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'
import { Toggle } from '@/components/ui/Toggle'

const CONFIG_DEFAULT: Configuracion = {
  valor_cuota: '50000.00',
  periodicidad_cuota: 'MENSUAL',
  dia_limite_pago: 5,
  permite_aportes_extra: true,
  tasa_interes_base: '2.0',
  tasa_interes_min: '1.0',
  tasa_interes_max: '3.0',
  max_prestamos_activos: 2,
  max_capital_vigente: '2000000.00',
  estrategia_distribucion: 'PROPORCIONAL_AHORRO',
}

const SIGUIENTE: Record<string, string | null> = {
  BORRADOR: 'ABIERTA',
  ABIERTA: 'EN_OPERACION',
  EN_OPERACION: 'PENDIENTE_LIQUIDACION',
  PENDIENTE_LIQUIDACION: null, // la liquidación se confirma en su asistente
  LIQUIDADA: 'ARCHIVADA',
  ARCHIVADA: null,
}

const ESTRATEGIAS = ['PARTES_IGUALES', 'PROPORCIONAL_AHORRO', 'PROPORCIONAL_TIEMPO']

function CamposConfig({
  cfg,
  set,
}: {
  cfg: Configuracion
  set: (c: Configuracion) => void
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Valor de la cuota" inputMode="decimal" value={cfg.valor_cuota}
        onChange={(e) => set({ ...cfg, valor_cuota: e.target.value })} />
      <SelectField label="Periodicidad" value={cfg.periodicidad_cuota}
        onChange={(e) => set({ ...cfg, periodicidad_cuota: e.target.value })}>
        {['MENSUAL', 'QUINCENAL', 'SEMANAL'].map((p) => <option key={p}>{p}</option>)}
      </SelectField>
      <Field label="Día límite de pago" type="number" min={1} max={31} value={cfg.dia_limite_pago}
        onChange={(e) => set({ ...cfg, dia_limite_pago: Number(e.target.value) })} />
      <SelectField label="Estrategia de reparto" value={cfg.estrategia_distribucion}
        onChange={(e) => set({ ...cfg, estrategia_distribucion: e.target.value })}>
        {ESTRATEGIAS.map((s) => <option key={s}>{s}</option>)}
      </SelectField>
      <Field label="Tasa base (%)" inputMode="decimal" value={cfg.tasa_interes_base}
        onChange={(e) => set({ ...cfg, tasa_interes_base: e.target.value })} />
      <div /> {/* espaciador para alinear la rejilla */}
      <Field label="Tasa mínima (%)" inputMode="decimal" value={cfg.tasa_interes_min}
        onChange={(e) => set({ ...cfg, tasa_interes_min: e.target.value })} />
      <Field label="Tasa máxima (%)" inputMode="decimal" value={cfg.tasa_interes_max}
        onChange={(e) => set({ ...cfg, tasa_interes_max: e.target.value })} />
      <Field label="Máx. préstamos activos" type="number" min={1} value={cfg.max_prestamos_activos}
        onChange={(e) => set({ ...cfg, max_prestamos_activos: Number(e.target.value) })} />
      <Field label="Máx. capital vigente" inputMode="decimal" value={cfg.max_capital_vigente}
        onChange={(e) => set({ ...cfg, max_capital_vigente: e.target.value })} />
      <div className="flex items-center justify-between rounded-nm-sm bg-surface px-4 py-2.5 shadow-nm-in sm:col-span-2">
        <div>
          <p className="text-sm font-medium">Permitir aportes extraordinarios</p>
          <p className="text-xs text-text-secondary">Aportes de monto libre además de la cuota.</p>
        </div>
        <Toggle
          activo={cfg.permite_aportes_extra}
          onChange={() => set({ ...cfg, permite_aportes_extra: !cfg.permite_aportes_extra })}
          etiqueta="Permitir aportes extraordinarios"
        />
      </div>
    </div>
  )
}

export function Natillera() {
  const nat = useAuth((s) => s.natilleraUuid)
  const detalle = useNatillera(nat)
  const configurar = useConfigurar(nat ?? '')
  const transicionar = useTransicionar(nat ?? '')
  const crear = useCrearNatillera()

  const [nueva, setNueva] = useState<NuevaNatillera>({
    nombre: '',
    ciclo_inicio: '2026-01-01',
    ciclo_fin: '2026-12-31',
    configuracion: { ...CONFIG_DEFAULT },
  })
  const [cfg, setCfg] = useState<Configuracion>({ ...CONFIG_DEFAULT })

  useEffect(() => {
    if (detalle.data?.configuracion) setCfg(detalle.data.configuracion)
  }, [detalle.data])

  const actual = detalle.data
  const siguiente = actual ? SIGUIENTE[actual.estado] : null

  function avanzar() {
    if (!siguiente) return
    let msg = `¿Avanzar la natillera a ${siguiente}?`
    if (siguiente === 'PENDIENTE_LIQUIDACION') {
      msg =
        '⚠️ ATENCIÓN: pasar a PENDIENTE DE LIQUIDACIÓN es IRREVERSIBLE y ' +
        'BLOQUEA cuotas, préstamos y actividades (solo quedará liquidar). ' +
        '¿Estás seguro de continuar?'
    } else if (siguiente === 'ARCHIVADA') {
      msg =
        '⚠️ ATENCIÓN: archivar la natillera es IRREVERSIBLE y la deja en ' +
        'solo lectura para siempre. ¿Continuar?'
    }
    if (confirm(msg)) transicionar.mutate(siguiente)
  }

  function onCrear(e: FormEvent) {
    e.preventDefault()
    crear.mutate(nueva, { onSuccess: () => setNueva({ ...nueva, nombre: '' }) })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Natillera</h1>
        <Ayuda id="natillera" />
      </div>

      {/* Natillera activa: estado + configuración */}
      {actual && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Building2 size={20} className="text-accent" />
              <div>
                <p className="font-semibold">{actual.nombre}</p>
                <p className="text-xs text-text-secondary">
                  Ciclo {actual.ciclo_inicio} → {actual.ciclo_fin}
                </p>
              </div>
            </div>
            <Badge tono={actual.estado === 'EN_OPERACION' ? 'acento' : 'neutro'}>{actual.estado}</Badge>
          </div>
          {siguiente && (
            <Button
              variante="primaria"
              cargando={transicionar.isPending}
              onClick={avanzar}
            >
              <StepForward size={16} /> Avanzar a {siguiente}
            </Button>
          )}
          {transicionar.isError && (
            <p className="mt-2 text-sm text-danger">{mensajeError(transicionar.error)}</p>
          )}
        </Card>
      )}

      {actual && (
        <Card>
          <CardTitulo>Configuración</CardTitulo>
          <CamposConfig cfg={cfg} set={setCfg} />
          <div className="mt-3 flex items-center justify-between">
            {configurar.isError ? (
              <p className="text-sm text-danger">{mensajeError(configurar.error)}</p>
            ) : (
              <span />
            )}
            <Button cargando={configurar.isPending} onClick={() => configurar.mutate(cfg)}>
              <Save size={16} /> Guardar configuración
            </Button>
          </div>
        </Card>
      )}

      {/* Crear una nueva natillera */}
      <Card>
        <CardTitulo>Crear nueva natillera</CardTitulo>
        <form onSubmit={onCrear} className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Nombre" value={nueva.nombre}
              onChange={(e) => setNueva({ ...nueva, nombre: e.target.value })} required />
            <Field label="Inicio del ciclo" type="date" value={nueva.ciclo_inicio}
              onChange={(e) => setNueva({ ...nueva, ciclo_inicio: e.target.value })} required />
            <Field label="Fin del ciclo" type="date" value={nueva.ciclo_fin}
              onChange={(e) => setNueva({ ...nueva, ciclo_fin: e.target.value })} required />
          </div>
          <CamposConfig
            cfg={nueva.configuracion ?? CONFIG_DEFAULT}
            set={(c) => setNueva({ ...nueva, configuracion: c })}
          />
          <div className="flex items-center justify-between">
            {crear.isError ? (
              <p className="text-sm text-danger">{mensajeError(crear.error)}</p>
            ) : (
              <span />
            )}
            <Button type="submit" variante="primaria" cargando={crear.isPending}>
              <PlusCircle size={16} /> Crear y activar
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
