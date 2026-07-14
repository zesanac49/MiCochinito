import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Asiento, CuentaParticipante, EstadoParticipante, Participante } from '@/types'

export function useParticipante(nat: string | null, uuid: string | null) {
  return useQuery({
    queryKey: ['participante', nat, uuid],
    enabled: !!nat && !!uuid,
    queryFn: async () =>
      (await api.get<Participante>(`/natilleras/${nat}/participantes/${uuid}`)).data,
  })
}

export function useCuenta(nat: string | null, uuid: string | null) {
  return useQuery({
    queryKey: ['cuenta', nat, uuid],
    enabled: !!nat && !!uuid,
    queryFn: async () =>
      (await api.get<CuentaParticipante>(`/natilleras/${nat}/participantes/${uuid}/cuenta`))
        .data,
  })
}

function invalidarCuenta(qc: ReturnType<typeof useQueryClient>, nat: string, uuid: string) {
  qc.invalidateQueries({ queryKey: ['cuenta', nat, uuid] })
  qc.invalidateQueries({ queryKey: ['fondos', nat] })
  qc.invalidateQueries({ queryKey: ['participantes', nat] })
}

export function useCambiarEstadoParticipante(nat: string, uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (estado: EstadoParticipante) =>
      (await api.post<Participante>(`/natilleras/${nat}/participantes/${uuid}/estado`, { estado }))
        .data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['participante', nat, uuid] })
      qc.invalidateQueries({ queryKey: ['participantes', nat] })
    },
  })
}

export function useAporteExtraordinario(nat: string, uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (monto: string) =>
      (
        await api.post<Asiento>(`/natilleras/${nat}/aportes-extraordinarios`, {
          participante_uuid: uuid,
          monto,
        })
      ).data,
    onSuccess: () => invalidarCuenta(qc, nat, uuid),
  })
}

export function usePagarCuota(nat: string, uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (periodoUuid: string) =>
      (
        await api.post<Asiento>(`/natilleras/${nat}/cuotas/pagos`, {
          participante_uuid: uuid,
          periodo_uuid: periodoUuid,
        })
      ).data,
    onSuccess: () => invalidarCuenta(qc, nat, uuid),
  })
}
