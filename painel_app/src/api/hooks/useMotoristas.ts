import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ENDPOINTS } from '../endpoints'
import { api } from '../client'
import type { UserPublic } from '../../types/api'

interface CreateMotoristaInput {
  nome: string
  email: string
  senha: string
  cpf: string
  telefone: string
  cnhVencimento: string
}

export function useMotoristas() {
  return useQuery({
    queryKey: ['users', 'motoristas'],
    queryFn: async () => {
      const { data } = await api.get<UserPublic[]>(ENDPOINTS.users.list, {
        params: { role: 'MOTORISTA' },
      })
      return data
    },
  })
}

export function useCreateMotorista() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: CreateMotoristaInput) => {
      const { data } = await api.post<UserPublic>(ENDPOINTS.auth.registrar, {
        nome: payload.nome,
        email: payload.email,
        senha: payload.senha,
        role: 'MOTORISTA',
        perfil_motorista: {
          cpf: payload.cpf,
          telefone: payload.telefone,
          cnh: {
            vencimento: payload.cnhVencimento,
          },
        },
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'motoristas'] })
    },
  })
}

export function useUpdateMotorista(userId?: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: {
      nome: string
      cpf: string
      telefone: string
      cnhVencimento: string
    }) => {
      if (!userId) throw new Error('Motorista inválido')
      const { data } = await api.patch<UserPublic>(ENDPOINTS.users.detail(userId), {
        nome: payload.nome,
        perfil_motorista: {
          cpf: payload.cpf,
          telefone: payload.telefone,
          cnh: {
            vencimento: payload.cnhVencimento,
          },
        },
      })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'motoristas'] })
    },
  })
}
