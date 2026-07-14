import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Dashboard, Liquidacion } from '@/types'

export function useLiquidacion(nat: string | null) {
  return useQuery({
    queryKey: ['liquidacion', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Liquidacion>(`/natilleras/${nat}/liquidacion`)).data,
  })
}

function useLiqAccion(nat: string, ruta: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (body?: unknown) =>
      (await api.post<Liquidacion>(`/natilleras/${nat}/liquidacion${ruta}`, body ?? {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['liquidacion', nat] })
      qc.invalidateQueries({ queryKey: ['fondos', nat] })
    },
  })
}

export const useIniciarLiquidacion = (nat: string) => useLiqAccion(nat, '')
export const useCalcularLiquidacion = (nat: string) => useLiqAccion(nat, '/calculo')
export const useConfirmarLiquidacion = (nat: string) => useLiqAccion(nat, '/confirmacion')

export function useDashboard(nat: string | null) {
  return useQuery({
    queryKey: ['dashboard', nat],
    enabled: !!nat,
    queryFn: async () => (await api.get<Dashboard>(`/natilleras/${nat}/dashboard`)).data,
  })
}
