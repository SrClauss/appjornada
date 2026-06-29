import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import api from '@/lib/api';
import type { Jornada } from '@/lib/types';

interface JornadasParams {
  data?: string;
  motorista_id?: string;
  status_filtro?: string;
  page?: number;
  size?: number;
  enabled?: boolean;
}

export function useJornadas(params: JornadasParams = {}) {
  const { page = 1, size = 50, enabled = true, ...rest } = params;
  const skip = (page - 1) * size;
  const limit = size;

  return useQuery({
    queryKey: ['jornadas', { skip, limit, ...rest }],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { skip, limit, ...rest },
      });
      return data;
    },
    staleTime: 15_000,
    enabled,
  });
}

export function useJornadasHoje() {
  const hoje = format(new Date(), 'yyyy-MM-dd');
  return useQuery({
    queryKey: ['jornadas', 'hoje', hoje],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { data: hoje, size: 100 },
      });
      return data;
    },
    staleTime: 15_000,
    refetchInterval: 60_000,
  });
}
