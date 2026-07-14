import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Actividad, TipoActividad } from '@/types'

export function useActividades(nat: string | null) {
  return useQuery({
    queryKey: ['actividades', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Actividad[]>(`/natilleras/${nat}/actividades`)).data,
  })
}

export function useActividad(nat: string | null, uuid: string | null) {
  return useQuery({
    queryKey: ['actividad', nat, uuid],
    enabled: !!nat && !!uuid,
    queryFn: async () =>
      (await api.get<Actividad>(`/natilleras/${nat}/actividades/${uuid}`)).data,
  })
}

export interface NuevaActividad {
  tipo: TipoActividad
  nombre: string
  periodo_uuid: string
  valor_numero?: string
  cantidad_numeros?: number
}

export function useCrearActividad(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (a: NuevaActividad) =>
      (await api.post<Actividad>(`/natilleras/${nat}/actividades`, a)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['actividades', nat] }),
  })
}

// Acción genérica sobre una actividad (apertura, pagos, sorteo, cierre, ...).
export function useAccionActividad(nat: string, uuid: string, ruta: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body?: unknown) =>
      (await api.post<Actividad>(`/natilleras/${nat}/actividades/${uuid}/${ruta}`, body ?? {}))
        .data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['actividad', nat, uuid] })
      qc.invalidateQueries({ queryKey: ['actividades', nat] })
      qc.invalidateQueries({ queryKey: ['fondos', nat] })
    },
  })
}

export function useAsignarNumeros(nat: string, uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body: { asignaciones: { numero: number; participante_uuid: string }[] }) =>
      (await api.put<Actividad>(`/natilleras/${nat}/actividades/${uuid}/numeros`, body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['actividad', nat, uuid] }),
  })
}
