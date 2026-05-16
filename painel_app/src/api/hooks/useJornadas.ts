import { useQuery } from '@tanstack/react-query'
import { ENDPOINTS } from '../endpoints'
import { api } from '../client'
import type { Jornada } from '../../types/api'

interface QueryParams {
  data?: string
  motorista_id?: string
  status_filtro?: string
  skip?: number
  limit?: number
}

export function useJornadas(params: QueryParams = {}) {
  return useQuery({
    queryKey: ['jornadas', params],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>(ENDPOINTS.jornadas.list, { params })
      return data
    },
  })
}
