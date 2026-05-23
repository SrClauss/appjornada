import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import api from '@/lib/api';
import type { Jornada, AlertaInatividade } from '@/lib/types';

export interface DashboardKPIs {
  motoristasAtivos: number;
  totalKmHoje: number;
  faturamentoHoje: number;
  totalAlertas: number;
  jornadasStatus: { name: string; value: number; color: string }[];
  faturamentoPorMotorista: { nome: string; total: number }[];
  alertas: AlertaInatividade[];
}

export function useDashboard() {
  const hoje = format(new Date(), 'yyyy-MM-dd');

  const jornadasQuery = useQuery({
    queryKey: ['dashboard', 'jornadas', hoje],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { data: hoje, size: 100 },
      });
      return data;
    },
    staleTime: 15_000,
    refetchInterval: 60_000,
  });

  const alertasQuery = useQuery({
    queryKey: ['dashboard', 'alertas'],
    queryFn: async () => {
      const { data } = await api.get<AlertaInatividade[]>('/gps/alertas-inatividade');
      return data;
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
  });

  const jornadas = jornadasQuery.data ?? [];
  const alertas = alertasQuery.data ?? [];

  const motoristasAtivos = jornadas.filter(
    (j) => j.status === 'ABERTA' || j.status === 'EM_ANDAMENTO' || j.status === 'EM_PAUSA',
  ).length;

  const totalKmHoje = jornadas.reduce((sum, j) => sum + (j.km?.rodados ?? 0), 0);

  const faturamentoHoje = jornadas.reduce(
    (sum, j) => sum + (j.faturamento?.total_dia ?? 0),
    0,
  );

  const jornadasStatus = [
    {
      name: 'Ativa',
      value: jornadas.filter(
        (j) => j.status === 'ABERTA' || j.status === 'EM_ANDAMENTO',
      ).length,
      color: '#3b82f6',
    },
    {
      name: 'Em Pausa',
      value: jornadas.filter((j) => j.status === 'EM_PAUSA').length,
      color: '#f59e0b',
    },
    {
      name: 'Encerrada',
      value: jornadas.filter((j) => j.status === 'ENCERRADA').length,
      color: '#10b981',
    },
  ];

  // Agrupa faturamento por motorista
  const mapaFaturamento: Record<string, number> = {};
  for (const j of jornadas) {
    const nome = j.motorista_nome ?? j.motorista_id;
    mapaFaturamento[nome] = (mapaFaturamento[nome] ?? 0) + (j.faturamento?.total_dia ?? 0);
  }
  const faturamentoPorMotorista = Object.entries(mapaFaturamento).map(
    ([nome, total]) => ({ nome: nome.split(' ')[0], total }),
  );

  return {
    isLoading: jornadasQuery.isLoading || alertasQuery.isLoading,
    isError: jornadasQuery.isError || alertasQuery.isError,
    kpis: {
      motoristasAtivos,
      totalKmHoje,
      faturamentoHoje,
      totalAlertas: alertas.length,
      jornadasStatus,
      faturamentoPorMotorista,
      alertas,
    } satisfies DashboardKPIs,
  };
}
