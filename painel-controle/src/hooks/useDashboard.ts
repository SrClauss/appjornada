import { useQuery } from '@tanstack/react-query';
import { format, startOfWeek, addDays, startOfMonth, getDaysInMonth } from 'date-fns';
import api from '@/lib/api';
import type { Jornada, AlertaInatividade } from '@/lib/types';

const META_HORAS_MENSAIS = 220;
const DAY_KEYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'];

export interface DashboardKPIs {
  motoristasAtivos: number;
  totalKmHoje: number;
  faturamentoHoje: number;
  totalAlertas: number;
  jornadasStatus: { name: string; value: number; color: string }[];
  faturamentoPorMotorista: { nome: string; total: number }[];
  alertas: AlertaInatividade[];
  weeklyRevenueByDriver: Array<Record<string, string | number>>;
  horasData: { day: number; hours: number; meta: number }[];
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
      return [];
    },
    staleTime: Infinity,
  });

  // Jornadas recentes (sem filtro de data) para cálculos semanais/mensais
  const recentQuery = useQuery({
    queryKey: ['dashboard', 'recent'],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', { params: { limit: 200 } });
      return data;
    },
    staleTime: 60_000,
    refetchInterval: 300_000,
  });

  const jornadas = jornadasQuery.data ?? [];
  const alertas = alertasQuery.data ?? [];
  const recentJornadas = recentQuery.data ?? [];

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

  // Faturamento semanal por motorista (Seg–Dom)
  const now = new Date();
  const weekStart = startOfWeek(now, { weekStartsOn: 1 });
  const weekDates = Array.from({ length: 7 }, (_, i) =>
    format(addDays(weekStart, i), 'yyyy-MM-dd'),
  );
  const driverDayMap: Record<string, Record<string, number>> = {};
  for (const j of recentJornadas) {
    const idx = weekDates.indexOf(j.data);
    if (idx === -1) continue;
    const nome = (j.motorista_nome ?? j.motorista_id).split(' ')[0];
    if (!driverDayMap[nome]) driverDayMap[nome] = {};
    const key = DAY_KEYS[idx];
    driverDayMap[nome][key] = (driverDayMap[nome][key] ?? 0) + (j.faturamento?.total_dia ?? 0);
  }
  const weeklyRevenueByDriver = Object.entries(driverDayMap).map(([name, days]) => ({
    name,
    ...Object.fromEntries(DAY_KEYS.map((k) => [k, days[k] ?? 0])),
  }));

  // Horas acumuladas no mês vs. meta CLT
  const monthStart = startOfMonth(now);
  const daysInMonth = getDaysInMonth(now);
  const monthStartStr = format(monthStart, 'yyyy-MM-dd');
  const todayStr = format(now, 'yyyy-MM-dd');
  const monthJornadas = recentJornadas.filter(
    (j) => j.data >= monthStartStr && j.data <= todayStr,
  );
  const hoursByDay: Record<string, number> = {};
  for (const j of monthJornadas) {
    hoursByDay[j.data] = (hoursByDay[j.data] ?? 0) + (j.horario?.total_horas_segundos ?? 0) / 3600;
  }
  let accumulated = 0;
  const horasData: { day: number; hours: number; meta: number }[] = [];
  for (let i = 1; i <= daysInMonth; i++) {
    const dateStr = format(new Date(now.getFullYear(), now.getMonth(), i), 'yyyy-MM-dd');
    if (dateStr <= todayStr) {
      accumulated += hoursByDay[dateStr] ?? 0;
      horasData.push({ day: i, hours: Math.round(accumulated * 10) / 10, meta: META_HORAS_MENSAIS });
    }
  }

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
      weeklyRevenueByDriver,
      horasData,
    } satisfies DashboardKPIs,
  };
}
