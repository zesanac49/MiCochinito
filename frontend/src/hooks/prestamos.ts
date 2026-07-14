import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { PagoPrestamoResultado, Prestamo } from '@/types'

export function usePrestamos(nat: string | null) {
  return useQuery({
    queryKey: ['prestamos', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Prestamo[]>(`/natilleras/${nat}/prestamos`)).data,
  })
}

export interface NuevoPrestamo {
  participante_uuid: string
  capital: string
  tasa: string
  plazo_meses: number
}

export function useSolicitarPrestamo(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (p: NuevoPrestamo) =>
      (await api.post<Prestamo>(`/natilleras/${nat}/prestamos`, p)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prestamos', nat] }),
  })
}

function usePrestamoAccion<TResp>(nat: string, ruta: (uuid: string) => string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ uuid, body }: { uuid: string; body?: unknown }) =>
      (await api.post<TResp>(`/natilleras/${nat}/prestamos/${ruta(uuid)}`, body ?? {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['prestamos', nat] })
      qc.invalidateQueries({ queryKey: ['fondos', nat] })
    },
  })
}

export function useAprobarPrestamo(nat: string) {
  return usePrestamoAccion<Prestamo>(nat, (u) => `${u}/aprobacion`)
}

export function useDesembolsar(nat: string) {
  return usePrestamoAccion<Prestamo>(nat, (u) => `${u}/desembolso`)
}

export function usePagarPrestamo(nat: string) {
  return usePrestamoAccion<PagoPrestamoResultado>(nat, (u) => `${u}/pagos`)
}

export function useDetectarMora(nat: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      (await api.post<{ marcados_en_mora: number }>(`/natilleras/${nat}/prestamos/mora`, {})).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prestamos', nat] }),
  })
}
