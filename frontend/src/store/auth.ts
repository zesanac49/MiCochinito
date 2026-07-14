import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Usuario } from '@/types'

interface AuthState {
  access: string | null
  refresh: string | null
  usuario: Usuario | null
  natilleraUuid: string | null
  setTokens: (access: string, refresh: string) => void
  setUsuario: (usuario: Usuario) => void
  setNatillera: (uuid: string | null) => void
  limpiar: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      access: null,
      refresh: null,
      usuario: null,
      natilleraUuid: null,
      setTokens: (access, refresh) => set({ access, refresh }),
      setUsuario: (usuario) =>
        set((s) => ({
          usuario,
          // Si no hay natillera activa, elige la primera membresía.
          natilleraUuid:
            s.natilleraUuid ?? usuario.membresias[0]?.natillera_uuid ?? null,
        })),
      setNatillera: (uuid) => set({ natilleraUuid: uuid }),
      limpiar: () =>
        set({ access: null, refresh: null, usuario: null, natilleraUuid: null }),
    }),
    { name: 'natillera-auth' },
  ),
)

export function rolActivo(): string | null {
  const { usuario, natilleraUuid } = useAuth.getState()
  const m = usuario?.membresias.find((x) => x.natillera_uuid === natilleraUuid)
  return m?.rol ?? null
}
