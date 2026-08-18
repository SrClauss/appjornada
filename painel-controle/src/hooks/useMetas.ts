import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { MetaBonus, CreateMetaPayload } from '@/lib/types';

export function useMetas() {
  return useQuery({
    queryKey: ['metas'],
    queryFn: async () => {
      try {
        const { data } = await api.get('/metas');
        if (Array.isArray(data)) return data as MetaBonus[];
        if (data && Array.isArray((data as any).items)) return (data as any).items as MetaBonus[];
        return [] as MetaBonus[];
      } catch (err) {
        console.error('Erro ao buscar metas:', err);
        return [] as MetaBonus[];
      }
    },
    staleTime: 60_000,
  });
}

export function useCreateMeta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateMetaPayload) => api.post('/metas', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['metas'] }),
  });
}

export function useUpdateMeta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CreateMetaPayload> }) =>
      api.patch(`/metas/${id}`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['metas'] }),
  });
}

export function useDeleteMeta() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/metas/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['metas'] }),
  });
}
