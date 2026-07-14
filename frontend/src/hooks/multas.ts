import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { CatalogoMulta, Multa } from '@/types'

export function useCatalogo(nat: string | null) {
  return useQuery({
    queryKey: ['catalogo', nat],
    enabled: !!nat,
    queryFn: async () =>
      (await api.get<CatalogoMulta[]>(`/natilleras/${nat}/catalogo-multas`)).data,
  })
}

export function useCrearCatalogo(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (e: { nombre: string; tipo: string; valor: string }) =>
      (await api.post<CatalogoMulta>(`/natilleras/${nat}/catalogo-multas`, e)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['catalogo', nat] }),
  })
}

export function useMultas(nat: string | null) {
  return useQuery({
    queryKey: ['multas', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Multa[]>(`/natilleras/${nat}/multas`)).data,
  })
}

export interface NuevaMulta {
  participante_uuid: string
  motivo: string
  catalogo_uuid?: string
  valor?: string
}

export function useImponerMulta(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (m: NuevaMulta) =>
      (await api.post<Multa>(`/natilleras/${nat}/multas`, m)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['multas', nat] }),
  })
}

function useMultaAccion(nat: string, ruta: (uuid: string) => string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ uuid, body }: { uuid: string; body?: unknown }) =>
      (await api.post<Multa>(`/natilleras/${nat}/multas/${ruta(uuid)}`, body ?? {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['multas', nat] })
      qc.invalidateQueries({ queryKey: ['fondos', nat] })
    },
  })
}

export function usePagarMulta(nat: string) {
  return useMultaAccion(nat, (u) => `${u}/pago`)
}

export function useAnularMulta(nat: string) {
  return useMultaAccion(nat, (u) => `${u}/anulacion`)
}
