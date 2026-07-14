import axios, { AxiosError, type AxiosRequestConfig } from 'axios'
import { useAuth } from '@/store/auth'
import type { ErrorApi, Tokens } from '@/types'

export const api = axios.create({ baseURL: '/api/v1' })

// Interceptor de request: adjunta el access token.
api.interceptors.request.use((config) => {
  const access = useAuth.getState().access
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

// Refresh con rotación: una sola petición de refresh en vuelo a la vez.
let refreshEnCurso: Promise<string | null> | null = null

async function refrescar(): Promise<string | null> {
  const refresh = useAuth.getState().refresh
  if (!refresh) return null
  try {
    const { data } = await axios.post<Tokens>('/api/v1/auth/refresh', {
      refresh_token: refresh,
    })
    useAuth.getState().setTokens(data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    useAuth.getState().limpiar()
    return null
  }
}

// Interceptor de response: ante 401, intenta refrescar y reintenta una vez.
api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _reintento?: boolean }
    const codigo = (error.response?.data as ErrorApi | undefined)?.error?.codigo
    const debeRefrescar =
      error.response?.status === 401 &&
      codigo === 'TOKEN_EXPIRADO' &&
      !original._reintento

    if (debeRefrescar) {
      original._reintento = true
      refreshEnCurso = refreshEnCurso ?? refrescar()
      const nuevo = await refreshEnCurso
      refreshEnCurso = null
      if (nuevo) {
        original.headers = { ...original.headers, Authorization: `Bearer ${nuevo}` }
        return api(original)
      }
    }
    return Promise.reject(error)
  },
)

// Extrae el mensaje de error uniforme de la API (doc 05 §7).
export function mensajeError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ErrorApi | undefined
    return data?.error?.mensaje ?? 'Ocurrió un error de red.'
  }
  return 'Ocurrió un error inesperado.'
}
