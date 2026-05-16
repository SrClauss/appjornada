import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../client'
import { ENDPOINTS } from '../endpoints'
import type { ComparativoResponse, RelatorioImportacaoResponse } from '../../types/api'

export type PlataformaRelatorio = 'UBER' | '99'

interface ComparativoParams {
  data?: string
  motorista_nome?: string
}

export function useComparativoRelatorio(params: ComparativoParams, enabled = true) {
  return useQuery({
    queryKey: ['relatorios', 'comparativo', params],
    enabled: enabled && Boolean(params.data),
    queryFn: async () => {
      const requestParams = {
        data: params.data,
        motorista_nome: params.motorista_nome || undefined,
      }
      const { data } = await api.get<ComparativoResponse>(ENDPOINTS.relatorios.comparativo, { params: requestParams })
      return data
    },
  })
}

export function useImportRelatorio() {
  return useMutation({
    mutationFn: async ({ plataforma, arquivo }: { plataforma: PlataformaRelatorio; arquivo: File }) => {
      const formData = new FormData()
      formData.append('arquivo', arquivo)
      const endpoint = plataforma === 'UBER' ? ENDPOINTS.relatorios.importarUber : ENDPOINTS.relatorios.importar99
      const { data } = await api.post<RelatorioImportacaoResponse>(endpoint, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return data
    },
  })
}
