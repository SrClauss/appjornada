import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { Veiculo, CreateVeiculoPayload, UpdateVeiculoPayload } from '@/lib/types';

export function useVeiculos() {
  return useQuery({
    queryKey: ['veiculos'],
    queryFn: async () => {
      const { data } = await api.get<any[]>('/veiculos');
      return data.map((v) => ({
        ...v,
        id: v.id || v._id,
      })) as Veiculo[];
    },
    staleTime: 30_000,
  });
}

export function useCreateVeiculo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateVeiculoPayload) => api.post('/veiculos', payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['veiculos'] }),
  });
}

export function useUpdateVeiculo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ placa, payload }: { placa: string; payload: UpdateVeiculoPayload }) =>
      api.patch(`/veiculos/${placa}`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['veiculos'] }),
  });
}

export function useDeleteVeiculo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (placa: string) => api.delete(`/veiculos/${placa}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['veiculos'] }),
  });
}
