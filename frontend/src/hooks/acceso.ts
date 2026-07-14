import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Miembro, Rol } from '@/types'

export interface NuevoMiembro {
  nombre: string
  email: string
  password: string
  rol: Rol
  participante_uuid?: string | null
}

export interface CambioRol {
  usuario_uuid: string
  rol: Rol
  participante_uuid?: string | null
}

export function useMiembros(nat: string | null) {
  return useQuery({
    queryKey: ['miembros', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Miembro[]>(`/natilleras/${nat}/miembros`)).data,
  })
}

export function useAgregarMiembro(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (m: NuevoMiembro) =>
      (await api.post(`/natilleras/${nat}/miembros`, m)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['miembros', nat] }),
  })
}

export function useCambiarRol(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ usuario_uuid, rol, participante_uuid }: CambioRol) =>
      (
        await api.patch(`/natilleras/${nat}/miembros/${usuario_uuid}`, {
          rol,
          participante_uuid: participante_uuid ?? null,
        })
      ).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['miembros', nat] }),
  })
}

export function useQuitarMiembro(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (usuario_uuid: string) =>
      (await api.delete(`/natilleras/${nat}/miembros/${usuario_uuid}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['miembros', nat] }),
  })
}

export function useReiniciarClave(nat: string) {
  return useMutation({
    mutationFn: async ({ usuario_uuid, password }: { usuario_uuid: string; password: string }) =>
      (await api.post(`/natilleras/${nat}/miembros/${usuario_uuid}/clave`, { password })).data,
  })
}
