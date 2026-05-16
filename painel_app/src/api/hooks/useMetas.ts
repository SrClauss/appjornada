import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../client'
import { ENDPOINTS } from '../endpoints'
import type { MetaBonus } from '../../types/api'

export interface MetaPayload {
  tipo: string
  referencia: string
  faixa_minima?: number
  faixa_maxima?: number
  bonus?: number
}

export function useMetas() {
  return useQuery({
    queryKey: ['metas'],
    queryFn: async () => {
      const { data } = await api.get<MetaBonus[]>(ENDPOINTS.metas.list)
      return data
    },
  })
}

export function useCreateMeta() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: MetaPayload) => {
      const { data } = await api.post<MetaBonus>(ENDPOINTS.metas.list, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metas'] })
    },
  })
}

export function useUpdateMeta(id?: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: Partial<MetaPayload>) => {
      if (!id) throw new Error('Meta inválida')
      const { data } = await api.patch<MetaBonus>(ENDPOINTS.metas.detail(id), payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metas'] })
    },
  })
}

export function useDeleteMeta() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(ENDPOINTS.metas.detail(id))
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['metas'] })
    },
  })
}
