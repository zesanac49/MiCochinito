import { useState } from 'react'
import { Ayuda } from '@/components/ui/Ayuda'
import { AlertTriangle, FileDown, Gavel } from 'lucide-react'
import { rolActivo, useAuth } from '@/store/auth'
import {
  useCalcularLiquidacion,
  useConfirmarLiquidacion,
  useIniciarLiquidacion,
  useLiquidacion,
} from '@/hooks/liquidacion'
import { mensajeError } from '@/lib/api'
import { formatoCOP } from '@/lib/formato'
import { exportarActaPDF } from '@/lib/exportar'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field } from '@/components/ui/Field'
import { Tabla, Td, Th, Tr } from '@/components/ui/Table'

export function Liquidacion() {
  const nat = useAuth((s) => s.natilleraUuid) ?? ''
  const usuario = useAuth((s) => s.usuario)
  const nombreNatillera =
    usuario?.membresias.find((m) => m.natillera_uuid === nat)?.natillera_nombre ?? ''

  const liq = useLiquidacion(nat)
  const iniciar = useIniciarLiquidacion(nat)
  const calcular = useCalcularLiquidacion(nat)
  const confirmar = useConfirmarLiquidacion(nat)
  const [nombre, setNombre] = useState('')

  const l = liq.data
  const iniciada = !!l?.uuid
  const bloqueos = l?.bloqueos ?? []

  if (rolActivo() !== 'ADMINISTRADOR') {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold tracking-tight">Liquidación</h1>
        <Card>
          <p className="text-sm text-text-secondary">
            Solo los <strong>administradores</strong> pueden liquidar la natillera.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">Liquidación</h1>
          <Ayuda id="liquidacion" />
        </div>
        {l && <Badge tono={l.fase === 'CONFIRMADA' ? 'acento' : 'neutro'}>{l.fase}</Badge>}
      </div>

      {/* Paso 1: iniciar / pre-validación */}
      {!iniciada && (
        <Card>
          <CardTitulo>Paso 1 · Pre-validación</CardTitulo>
          <p className="mb-3 text-sm text-text-secondary">
            Inicia el proceso para detectar bloqueos (préstamos sin pagar, actividades abiertas).
          </p>
          <Button variante="primaria" cargando={iniciar.isPending} onClick={() => iniciar.mutate(undefined)}>
            <Gavel size={16} /> Iniciar liquidación
          </Button>
          {iniciar.isError && <p className="mt-2 text-sm text-danger">{mensajeError(iniciar.error)}</p>}
        </Card>
      )}

      {iniciada && bloqueos.length > 0 && (
        <Card>
          <CardTitulo>Bloqueos por resolver</CardTitulo>
          <ul className="space-y-2">
            {bloqueos.map((b) => (
              <li key={`${b.origen_tipo}-${b.origen_id}`} className="flex items-center gap-2 text-sm">
                <AlertTriangle size={16} className="text-warning" />
                {b.descripcion} (#{b.origen_id})
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Paso 2: cálculo */}
      {iniciada && bloqueos.length === 0 && l?.fase === 'PRE_VALIDACION' && (
        <Card>
          <CardTitulo>Paso 2 · Cálculo</CardTitulo>
          <Button variante="primaria" cargando={calcular.isPending} onClick={() => calcular.mutate(undefined)}>
            Calcular liquidación
          </Button>
          {calcular.isError && <p className="mt-2 text-sm text-danger">{mensajeError(calcular.error)}</p>}
        </Card>
      )}

      {/* Detalle por participante */}
      {l && l.detalles.length > 0 && (
        <Card well>
          <CardTitulo>Detalle por participante</CardTitulo>
          <Tabla>
            <thead>
              <tr>
                <Th>Participante</Th>
                <Th right>Ahorros</Th>
                <Th right>Rentabilidad</Th>
                <Th right>Saldo final</Th>
              </tr>
            </thead>
            <tbody>
              {l.detalles.map((d) => (
                <Tr key={d.participante_uuid}>
                  <Td>{d.participante_nombre}</Td>
                  <Td right tabular>{formatoCOP(d.ahorros)}</Td>
                  <Td right tabular>{formatoCOP(d.participacion_rentabilidad)}</Td>
                  <Td right tabular>{formatoCOP(d.saldo_final)}</Td>
                </Tr>
              ))}
            </tbody>
          </Tabla>
        </Card>
      )}

      {/* Paso 3: confirmación con doble verificación */}
      {l?.fase === 'CALCULADA' && (
        <Card>
          <CardTitulo>Paso 3 · Confirmación irreversible</CardTitulo>
          <p className="mb-3 text-sm text-text-secondary">
            Escribe el nombre exacto de la natillera para confirmar. Esta acción es irreversible.
          </p>
          <div className="flex items-end gap-2">
            <Field
              label={`Nombre: "${nombreNatillera}"`}
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
            <Button
              variante="primaria"
              cargando={confirmar.isPending}
              disabled={!nombre}
              onClick={() => confirmar.mutate({ nombre_natillera: nombre })}
            >
              Confirmar
            </Button>
          </div>
          {confirmar.isError && <p className="mt-2 text-sm text-danger">{mensajeError(confirmar.error)}</p>}
        </Card>
      )}

      {/* Acta */}
      {l?.fase === 'CONFIRMADA' && (
        <Card>
          <CardTitulo>Acta de liquidación</CardTitulo>
          <p className="mb-3 text-sm text-text-secondary">
            La natillera quedó liquidada. Descarga el acta en PDF.
          </p>
          <Button onClick={() => exportarActaPDF(nombreNatillera, l.detalles)}>
            <FileDown size={16} /> Descargar acta (PDF)
          </Button>
        </Card>
      )}
    </div>
  )
}
