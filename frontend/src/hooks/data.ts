import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type {
  Fondo,
  Participante,
  Periodo,
  ResumenLote,
  TipoDocumento,
} from '@/types'

export function useParticipantes(nat: string | null) {
  return useQuery({
    queryKey: ['participantes', nat],
    enabled: !!nat,
    queryFn: async () =>
      (await api.get<Participante[]>(`/natilleras/${nat}/participantes`)).data,
  })
}

export interface NuevoParticipante {
  nombre: string
  tipo_documento: TipoDocumento
  numero_documento: string
  fecha_ingreso: string
  telefono?: string
}

export function useCrearParticipante(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (p: NuevoParticipante) =>
      (await api.post<Participante>(`/natilleras/${nat}/participantes`, p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['participantes', nat] }),
  })
}

export function usePeriodos(nat: string | null) {
  return useQuery({
    queryKey: ['periodos', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Periodo[]>(`/natilleras/${nat}/periodos`)).data,
  })
}

export function useFondos(nat: string | null) {
  return useQuery({
    queryKey: ['fondos', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Fondo[]>(`/natilleras/${nat}/fondos`)).data,
  })
}

export interface ItemLote {
  participante_uuid: string
  periodo_uuid: string
}

export function usePagarLote(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (items: ItemLote[]) =>
      (await api.post<ResumenLote>(`/natilleras/${nat}/cuotas/pagos-lote`, { items })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fondos', nat] })
      qc.invalidateQueries({ queryKey: ['participantes', nat] })
    },
  })
}
