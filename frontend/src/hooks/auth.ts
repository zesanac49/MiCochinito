import { useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/store/auth'
import type { Tokens, Usuario } from '@/types'

export function useLogin() {
  const setTokens = useAuth((s) => s.setTokens)
  const setUsuario = useAuth((s) => s.setUsuario)
  return useMutation({
    mutationFn: async (creds: { email: string; password: string }) => {
      const { data: tokens } = await api.post<Tokens>('/auth/login', creds)
      setTokens(tokens.access_token, tokens.refresh_token)
      const { data: me } = await api.get<Usuario>('/auth/me')
      setUsuario(me)
      return me
    },
  })
}
