import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../client'
import { ENDPOINTS } from '../endpoints'
import type { Veiculo } from '../../types/api'

export interface VeiculoPayload {
  id_placa: string
  marca_modelo?: string
  ano_modelo?: string
  cor?: string
  situacao: string
  km_atual?: number
  vencimento_ipva?: string
  imagem_clrv_url?: string
}

export function useVeiculos() {
  return useQuery({
    queryKey: ['veiculos'],
    queryFn: async () => {
      const { data } = await api.get<Veiculo[]>(ENDPOINTS.veiculos.list)
      return data
    },
  })
}

export function useCreateVeiculo() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: VeiculoPayload) => {
      const { data } = await api.post<Veiculo>(ENDPOINTS.veiculos.list, payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
    },
  })
}

export function useUpdateVeiculo(placa?: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: Omit<VeiculoPayload, 'id_placa'>) => {
      if (!placa) throw new Error('Veículo inválido')
      const { data } = await api.patch<Veiculo>(ENDPOINTS.veiculos.detail(placa), payload)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['veiculos'] })
    },
  })
}
