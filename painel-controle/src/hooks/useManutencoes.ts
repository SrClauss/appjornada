import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { Manutencao, CreateManutencaoPayload } from '@/lib/types';

export function useManutencoes(veiculo_id?: string) {
  return useQuery({
    queryKey: ['manutencoes', veiculo_id],
    queryFn: async () => {
      const { data } = await api.get<Manutencao[]>('/manutencoes', {
        params: veiculo_id ? { veiculo_id } : undefined,
      });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useCreateManutencao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateManutencaoPayload) => api.post('/manutencoes', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['manutencoes'] }),
  });
}

export function useUpdateManutencao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Manutencao> }) =>
      api.patch(`/manutencoes/${id}`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['manutencoes'] }),
  });
}
