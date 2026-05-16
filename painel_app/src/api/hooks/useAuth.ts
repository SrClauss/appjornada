import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '../endpoints'
import { api } from '../client'
import type { TokenResponse, UserPublic } from '../../types/api'
import { TOKEN_KEY } from '../../lib/utils'

export function useCurrentUser(enabled: boolean) {
  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const { data } = await api.get<UserPublic>(ENDPOINTS.auth.me)
      return data
    },
    enabled,
    retry: 1,
  })
}

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ email, senha }: { email: string; senha: string }) => {
      const form = new URLSearchParams()
      form.set('username', email)
      form.set('password', senha)

      const tokenResponse = await api.post<TokenResponse>(ENDPOINTS.auth.login, form, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      })

      localStorage.setItem(TOKEN_KEY, tokenResponse.data.access_token)

      const { data: user } = await api.get<UserPublic>(ENDPOINTS.auth.me)
      return user
    },
    onSuccess: (user) => {
      queryClient.setQueryData(['auth', 'me'], user)
    },
  })
}
