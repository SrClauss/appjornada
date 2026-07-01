import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { User, CreateUserPayload, UpdateUserPayload } from '@/lib/types';

export function useMotoristas(search = '') {
  return useQuery({
    queryKey: ['motoristas', search],
    queryFn: async () => {
      const params: Record<string, string> = { role: 'MOTORISTA', size: '100' };
      if (search) params.nome = search;
      const { data } = await api.get<User[]>('/users', { params });
      return data;
    },
    staleTime: 30_000,
  });
}

export function useAllUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const { data } = await api.get<User[]>('/users', { params: { size: '200' } });
      return data;
    },
    staleTime: 60_000,
  });
}

export function useCreateMotorista() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateUserPayload) => api.post('/auth/registrar', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['motoristas'] });
      qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateUserPayload }) =>
      api.patch(`/users/${id}`, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['motoristas'] });
      qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/users/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['motoristas'] });
      qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
