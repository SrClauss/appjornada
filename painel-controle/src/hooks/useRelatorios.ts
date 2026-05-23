import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import type { ComparativoItem } from '@/lib/types';

export function useComparativo(data?: string, motorista_nome?: string) {
  return useQuery({
    queryKey: ['relatorios', 'comparativo', data, motorista_nome],
    queryFn: async () => {
      const { data: res } = await api.get<ComparativoItem[]>('/relatorios/comparativo', {
        params: { data, motorista_nome },
      });
      return res;
    },
    enabled: !!data,
    staleTime: 60_000,
  });
}

export function useImportarCSV() {
  return useMutation({
    mutationFn: async ({ tipo, file }: { tipo: 'uber' | '99'; file: File }) => {
      const form = new FormData();
      form.append('file', file);
      const { data } = await api.post(`/relatorios/importar/${tipo}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data;
    },
  });
}
