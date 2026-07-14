import { useAuth } from '@/store/auth'
import { SelectField } from '@/components/ui/Field'

// Selector de natillera a partir de las membresías (/auth/me).
export function SelectorNatillera() {
  const usuario = useAuth((s) => s.usuario)
  const natilleraUuid = useAuth((s) => s.natilleraUuid)
  const setNatillera = useAuth((s) => s.setNatillera)
  const membresias = usuario?.membresias ?? []

  if (membresias.length === 0) {
    return <p className="text-sm text-text-secondary">Sin natilleras asignadas.</p>
  }

  return (
    <SelectField
      label="Natillera activa"
      value={natilleraUuid ?? ''}
      onChange={(e) => setNatillera(e.target.value)}
    >
      {membresias.map((m) => {
        const cerrada = m.natillera_estado === 'ARCHIVADA' || m.natillera_estado === 'LIQUIDADA'
        return (
          <option key={m.natillera_uuid} value={m.natillera_uuid}>
            {m.natillera_nombre} · {m.rol.toLowerCase()}
            {cerrada ? ` (${m.natillera_estado.toLowerCase()})` : ''}
          </option>
        )
      })}
    </SelectField>
  )
}
