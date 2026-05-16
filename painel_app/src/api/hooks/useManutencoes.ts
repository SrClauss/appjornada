import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../client'
import { ENDPOINTS } from '../endpoints'
import type { Localizacao, Manutencao, ServicoManutencao } from '../../types/api'

interface ManutencoesQueryParams {
  veiculo_id?: string
}

export interface CreateManutencaoPayload {
  jornada_id?: string
  motorista_id?: string
  veiculo_id: string
  entrada?: string
  saida?: string
  duracao_minutos?: number
  localizacao?: Localizacao
  decisao?: string
  km?: number
  km_proxima_revisao?: number
  status: string
  oficina?: string
  servico?: ServicoManutencao
}

export interface UpdateManutencaoPayload {
  saida?: string
  duracao_minutos?: number
  decisao?: string
  km?: number
  km_proxima_revisao?: number
  status?: string
  oficina?: string
  servico?: ServicoManutencao
}

export function useManutencoes(params: ManutencoesQueryParams = {}) {
  return useQuery({
    queryKey: ['manutencoes', params],
    queryFn: async () => {
      const { data } = await api.get<Manutencao[]>(ENDPOINTS.manutencoes.list, { params })
      return data
    },
  })
}

export function useCreateManutencao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: CreateManutencaoPayload) => {
      const { data } = await api.post<Manutencao>(ENDPOINTS.manutencoes.list, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
    },
  })
}

export function useUpdateManutencao(id?: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: UpdateManutencaoPayload) => {
      if (!id) throw new Error('Manutenção inválida')
      const { data } = await api.patch<Manutencao>(ENDPOINTS.manutencoes.detail(id), payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['manutencoes'] })
    },
  })
}
