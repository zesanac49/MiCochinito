import { type FormEvent, useState } from 'react'
import { KeyRound, ShieldCheck, Trash2, UserPlus } from 'lucide-react'
import { rolActivo, useAuth } from '@/store/auth'
import { useParticipantes } from '@/hooks/data'
import {
  type NuevoMiembro,
  useAgregarMiembro,
  useCambiarRol,
  useMiembros,
  useQuitarMiembro,
  useReiniciarClave,
} from '@/hooks/acceso'
import { mensajeError } from '@/lib/api'
import type { Miembro, Participante, Rol } from '@/types'
import { Ayuda } from '@/components/ui/Ayuda'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardTitulo } from '@/components/ui/Card'
import { Field, SelectField } from '@/components/ui/Field'

const ROLES: Rol[] = ['ADMINISTRADOR', 'SUPERVISOR', 'CLIENTE']

const TONO_ROL = {
  ADMINISTRADOR: 'acento',
  SUPERVISOR: 'alerta',
  CLIENTE: 'neutro',
} as const

const DESC_ROL: Record<Rol, string> = {
  ADMINISTRADOR: 'Control total, incluida la gestión de accesos.',
  SUPERVISOR: 'Gestiona casi toda la natillera (préstamos, multas, actividades, config). No puede liquidar ni gestionar usuarios.',
  CLIENTE: 'Solo lectura de lo suyo; se vincula a un participante.',
}

const VACIO: NuevoMiembro = {
  nombre: '',
  email: '',
  password: '',
  rol: 'SUPERVISOR',
  participante_uuid: null,
}

export function Usuarios() {
  const nat = useAuth((s) => s.natilleraUuid)
  const esAdmin = rolActivo() === 'ADMINISTRADOR'
  const miembros = useMiembros(nat)
  const participantes = useParticipantes(esAdmin ? nat : null)

  if (!esAdmin) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Usuarios y accesos</h1>
        <Ayuda id="usuarios" />
      </div>
        <Card>
          <p className="text-sm text-text-secondary">
            Esta sección es solo para <strong>administradores</strong> de la natillera.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Usuarios y accesos</h1>
        <Ayuda id="usuarios" />
      </div>

      {nat && (
        <FormularioAgregar nat={nat} participantes={participantes.data ?? []} />
      )}

      <Card well>
        <CardTitulo>Miembros ({miembros.data?.length ?? 0})</CardTitulo>
        <div className="space-y-3">
          {miembros.data?.map((m) => (
            <FilaMiembro
              key={m.usuario_uuid}
              nat={nat ?? ''}
              miembro={m}
              participantes={participantes.data ?? []}
            />
          ))}
          {miembros.data?.length === 0 && (
            <p className="text-sm text-text-secondary">Aún no hay miembros.</p>
          )}
        </div>
      </Card>
    </div>
  )
}

function FormularioAgregar({
  nat,
  participantes,
}: {
  nat: string
  participantes: Participante[]
}) {
  const agregar = useAgregarMiembro(nat)
  const [form, setForm] = useState<NuevoMiembro>(VACIO)

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    const payload: NuevoMiembro = {
      ...form,
      participante_uuid: form.rol === 'CLIENTE' ? form.participante_uuid : null,
    }
    agregar.mutate(payload, { onSuccess: () => setForm(VACIO) })
  }

  return (
    <Card>
      <CardTitulo>Dar acceso a una persona</CardTitulo>
      <form onSubmit={onSubmit} className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Nombre"
          value={form.nombre}
          onChange={(e) => setForm({ ...form, nombre: e.target.value })}
          required
        />
        <Field
          label="Correo"
          type="email"
          autoComplete="off"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
        <Field
          label="Contraseña temporal"
          type="text"
          autoComplete="off"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
          minLength={8}
        />
        <SelectField
          label="Rol"
          value={form.rol}
          onChange={(e) => setForm({ ...form, rol: e.target.value as Rol })}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </SelectField>

        {form.rol === 'CLIENTE' && (
          <SelectField
            label="Participante vinculado"
            value={form.participante_uuid ?? ''}
            onChange={(e) => setForm({ ...form, participante_uuid: e.target.value })}
            required
          >
            <option value="">Selecciona…</option>
            {participantes.map((p) => (
              <option key={p.uuid} value={p.uuid}>
                {p.nombre} — {p.numero_documento}
              </option>
            ))}
          </SelectField>
        )}

        <p className="text-xs text-text-secondary sm:col-span-2">{DESC_ROL[form.rol]}</p>

        <div className="flex items-center justify-between sm:col-span-2">
          {agregar.isError ? (
            <p className="text-sm text-danger">{mensajeError(agregar.error)}</p>
          ) : (
            <span className="text-xs text-text-secondary">
              La persona ingresa con el correo y la contraseña temporal.
            </span>
          )}
          <Button type="submit" variante="primaria" cargando={agregar.isPending}>
            <UserPlus size={16} /> Dar acceso
          </Button>
        </div>
      </form>
    </Card>
  )
}

function FilaMiembro({
  nat,
  miembro,
  participantes,
}: {
  nat: string
  miembro: Miembro
  participantes: Participante[]
}) {
  const cambiar = useCambiarRol(nat)
  const quitar = useQuitarMiembro(nat)
  const reiniciar = useReiniciarClave(nat)

  const [rol, setRol] = useState<Rol>(miembro.rol)
  const [participanteUuid, setParticipanteUuid] = useState<string>(
    miembro.participante_uuid ?? '',
  )
  const [clave, setClave] = useState('')
  const [mostrarClave, setMostrarClave] = useState(false)

  const cambioPendiente =
    rol !== miembro.rol ||
    (rol === 'CLIENTE' && participanteUuid !== (miembro.participante_uuid ?? ''))

  function guardarRol() {
    cambiar.mutate({
      usuario_uuid: miembro.usuario_uuid,
      rol,
      participante_uuid: rol === 'CLIENTE' ? participanteUuid : null,
    })
  }

  function reiniciarClave() {
    reiniciar.mutate(
      { usuario_uuid: miembro.usuario_uuid, password: clave },
      { onSuccess: () => { setClave(''); setMostrarClave(false) } },
    )
  }

  return (
    <div className="rounded-nm-sm bg-surface p-4 shadow-nm-in">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium">{miembro.nombre}</p>
          <p className="truncate text-xs text-text-secondary">{miembro.email}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tono={TONO_ROL[miembro.rol]}>{miembro.rol}</Badge>
          {miembro.participante_nombre && (
            <Badge tono="neutro">↳ {miembro.participante_nombre}</Badge>
          )}
        </div>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectField
            label="Rol"
            value={rol}
            onChange={(e) => setRol(e.target.value as Rol)}
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </SelectField>
          {rol === 'CLIENTE' && (
            <SelectField
              label="Participante"
              value={participanteUuid}
              onChange={(e) => setParticipanteUuid(e.target.value)}
            >
              <option value="">Selecciona…</option>
              {participantes.map((p) => (
                <option key={p.uuid} value={p.uuid}>
                  {p.nombre}
                </option>
              ))}
            </SelectField>
          )}
        </div>
        {cambioPendiente && (
          <Button variante="primaria" cargando={cambiar.isPending} onClick={guardarRol}>
            <ShieldCheck size={16} /> Guardar rol
          </Button>
        )}
      </div>

      {cambiar.isError && (
        <p className="mt-2 text-sm text-danger">{mensajeError(cambiar.error)}</p>
      )}

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-text-secondary/10 pt-3">
        {!mostrarClave ? (
          <Button variante="neutra" onClick={() => setMostrarClave(true)}>
            <KeyRound size={16} /> Reiniciar clave
          </Button>
        ) : (
          <div className="flex flex-1 flex-wrap items-end gap-2">
            <div className="min-w-[180px] flex-1">
              <Field
                label="Nueva contraseña temporal"
                type="text"
                autoComplete="off"
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                minLength={8}
              />
            </div>
            <Button
              variante="primaria"
              cargando={reiniciar.isPending}
              disabled={clave.length < 8}
              onClick={reiniciarClave}
            >
              Guardar clave
            </Button>
            <Button variante="neutra" onClick={() => { setMostrarClave(false); setClave('') }}>
              Cancelar
            </Button>
          </div>
        )}

        <Button
          variante="peligro"
          cargando={quitar.isPending}
          onClick={() => {
            if (confirm(`¿Quitar el acceso de ${miembro.nombre}?`)) {
              quitar.mutate(miembro.usuario_uuid)
            }
          }}
        >
          <Trash2 size={16} /> Quitar
        </Button>
      </div>

      {reiniciar.isSuccess && !mostrarClave && (
        <p className="mt-2 text-sm text-accent">Contraseña actualizada.</p>
      )}
      {quitar.isError && (
        <p className="mt-2 text-sm text-danger">{mensajeError(quitar.error)}</p>
      )}
    </div>
  )
}
