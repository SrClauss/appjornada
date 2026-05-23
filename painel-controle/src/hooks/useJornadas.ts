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
}

export function useJornadas(params: JornadasParams = {}) {
  return useQuery({
    queryKey: ['jornadas', params],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { size: 50, ...params },
      });
      return data;
    },
    staleTime: 15_000,
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
