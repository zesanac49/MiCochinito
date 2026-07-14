import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/store/auth'
import type { Natillera, Usuario } from '@/types'

export interface Configuracion {
  valor_cuota: string
  periodicidad_cuota: string
  dia_limite_pago: number
  permite_aportes_extra: boolean
  tasa_interes_base: string
  tasa_interes_min: string
  tasa_interes_max: string
  max_prestamos_activos: number
  max_capital_vigente: string
  estrategia_distribucion: string
}

export interface NatilleraDetalle extends Natillera {
  ciclo_inicio: string
  ciclo_fin: string
  configuracion: Configuracion | null
}

export function useNatillera(uuid: string | null) {
  return useQuery({
    queryKey: ['natillera', uuid],
    enabled: !!uuid,
    queryFn: async () => (await api.get<NatilleraDetalle>(`/natilleras/${uuid}`)).data,
  })
}

export interface NuevaNatillera {
  nombre: string
  ciclo_inicio: string
  ciclo_fin: string
  configuracion?: Configuracion
}

export function useCrearNatillera() {
  const qc = useQueryClient()
  const setUsuario = useAuth((s) => s.setUsuario)
  const setNatillera = useAuth((s) => s.setNatillera)
  return useMutation({
    mutationFn: async (n: NuevaNatillera) =>
      (await api.post<Natillera>('/natilleras', n)).data,
    onSuccess: async (nat) => {
      // Refresca las membresías (el creador quedó ADMINISTRADOR) y activa la nueva.
      const me = (await api.get<Usuario>('/auth/me')).data
      setUsuario(me)
      setNatillera(nat.uuid)
      qc.invalidateQueries()
    },
  })
}

export function useConfigurar(uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (cfg: Configuracion) =>
      (await api.put<Natillera>(`/natilleras/${uuid}/configuracion`, cfg)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['natillera', uuid] }),
  })
}

export function useTransicionar(uuid: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (a: string) =>
      (await api.post<Natillera>(`/natilleras/${uuid}/transiciones`, { a })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['natillera', uuid] })
      qc.invalidateQueries({ queryKey: ['periodos', uuid] })
    },
  })
}
