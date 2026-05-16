import { createContext, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogin } from '../api/hooks/useAuth'
import type { UserPublic } from '../types/api'
import { TOKEN_KEY } from '../lib/utils'

interface AuthContextType {
  user: UserPublic | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, senha: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(localStorage.getItem(TOKEN_KEY)))
  const loginMutation = useLogin()
  const meQuery = useCurrentUser(isAuthenticated)

  const value = useMemo<AuthContextType>(() => ({
    user: meQuery.data ?? null,
    isAuthenticated,
    isLoading: meQuery.isFetching || loginMutation.isPending,
    login: async (email: string, senha: string) => {
      const user = await loginMutation.mutateAsync({ email, senha })
      if (user.role === 'MOTORISTA') {
        localStorage.removeItem(TOKEN_KEY)
        setIsAuthenticated(false)
        throw new Error('Usuário MOTORISTA não pode acessar o painel administrativo.')
      }
      setIsAuthenticated(true)
      navigate('/')
    },
    logout: () => {
      localStorage.removeItem(TOKEN_KEY)
      setIsAuthenticated(false)
      navigate('/login')
    },
  }), [isAuthenticated, loginMutation, meQuery.data, meQuery.isFetching, navigate])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export { AuthContext }
