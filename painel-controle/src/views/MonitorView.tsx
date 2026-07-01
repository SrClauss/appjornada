import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import type { Jornada, Veiculo } from '@/lib/types';
import { 
  Users, 
  Car, 
  CurrencyDollar, 
  GasPump, 
  Wrench, 
  Clock, 
  ArrowClockwise, 
  ArrowLeft,
  Circle
} from '@phosphor-icons/react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

export function MonitorView() {
  const [hoje, setHoje] = useState('');

  useEffect(() => {
    const localDate = new Date();
    const yyyy = localDate.getFullYear();
    const mm = String(localDate.getMonth() + 1).padStart(2, '0');
    const dd = String(localDate.getDate()).padStart(2, '0');
    setHoje(`${yyyy}-${mm}-${dd}`);
  }, []);

  const { 
    data: jornadas = [], 
    isLoading: loadingJornadas, 
    refetch: refetchJornadas,
    isRefetching: refetchingJornadas
  } = useQuery({
    queryKey: ['monitor-jornadas', hoje],
    queryFn: async () => {
      if (!hoje) return [];
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { data: hoje, size: 100 },
      });
      return data;
    },
    enabled: !!hoje,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  const { 
    data: veiculos = [], 
    isLoading: loadingVeiculos, 
    refetch: refetchVeiculos,
    isRefetching: refetchingVeiculos
  } = useQuery({
    queryKey: ['monitor-veiculos'],
    queryFn: async () => {
      const { data } = await api.get<any[]>('/veiculos');
      return data.map((v) => ({
        ...v,
        id: v.id || v._id,
      })) as Veiculo[];
    },
    refetchInterval: 15000,
  });

  const handleManualRefresh = () => {
    refetchJornadas();
    refetchVeiculos();
  };

  const handleGoBack = () => {
    window.location.hash = '/dashboard';
  };

  // KPIs Calculations
  const activeJourneys = jornadas.filter(
    (j) => j.status === 'ABERTA' || j.status === 'EM_ANDAMENTO' || j.status === 'EM_PAUSA'
  );
  
  const motoristasAndando = activeJourneys.filter(
    (j) => j.status === 'EM_ANDAMENTO' || j.status === 'ABERTA'
  ).length;

  const motoristasPausa = activeJourneys.filter(
    (j) => j.status === 'EM_PAUSA'
  ).length;

  const faturamentoHoje = jornadas.reduce(
    (sum, j) => sum + (j.faturamento?.total_dia ?? 0),
    0
  );

  let totalCombustivelHoje = 0;
  for (const j of jornadas) {
    for (const ab of (j.abastecimentos ?? [])) {
      totalCombustivelHoje += (ab.valor_gasolina ?? 0) + (ab.valor_gnv ?? 0) + (ab.valor_etanol ?? 0);
    }
  }

  const veiculosManutencao = veiculos.filter(
    (v) => v.situacao === 'MANUTENCAO'
  );

  const formatCurrency = (v: number) =>
    v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  const isGlobalLoading = loadingJornadas || loadingVeiculos;
  const isGlobalRefetching = refetchingJornadas || refetchingVeiculos;

  return (
    <div className="flex flex-col min-h-screen bg-slate-950 text-slate-100 pb-8">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-slate-900/80 backdrop-blur-md border-b border-slate-800">
        <div className="flex items-center gap-2">
          <button 
            onClick={handleGoBack}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-md font-bold tracking-tight text-white flex items-center gap-2">
              Painel Monitor PWA
              {isGlobalRefetching && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-400">Torre de Controle Operacional</p>
          </div>
        </div>

        <button
          onClick={handleManualRefresh}
          disabled={isGlobalLoading}
          className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 transition-colors flex items-center gap-1.5 text-xs"
        >
          <ArrowClockwise size={14} className={isGlobalRefetching ? 'animate-spin' : ''} />
          {isGlobalRefetching ? 'Carregando...' : 'Atualizar'}
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 space-y-5">
        {isGlobalLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full bg-slate-900 rounded-xl" />
            <Skeleton className="h-48 w-full bg-slate-900 rounded-xl" />
            <Skeleton className="h-48 w-full bg-slate-900 rounded-xl" />
          </div>
        ) : (
          <>
            {/* KPI Cards Grid */}
            <div className="grid grid-cols-2 gap-3">
              {/* Andando Card */}
              <div className="p-3 bg-gradient-to-br from-emerald-950/40 to-slate-900 border border-emerald-900/30 rounded-xl shadow-md flex flex-col justify-between h-24">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">Rodando</span>
                  <div className="p-1 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Circle weight="fill" size={14} className="animate-pulse" />
                  </div>
                </div>
                <div>
                  <div className="text-2xl font-black text-white">{motoristasAndando}</div>
                  <div className="text-[10px] text-slate-400">Motoristas Ativos</div>
                </div>
              </div>

              {/* Pausa Card */}
              <div className="p-3 bg-gradient-to-br from-amber-950/40 to-slate-900 border border-amber-900/30 rounded-xl shadow-md flex flex-col justify-between h-24">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider">Pausa</span>
                  <div className="p-1 rounded-lg bg-amber-500/10 text-amber-400">
                    <Clock size={16} />
                  </div>
                </div>
                <div>
                  <div className="text-2xl font-black text-white">{motoristasPausa}</div>
                  <div className="text-[10px] text-slate-400">Em Intervalo</div>
                </div>
              </div>

              {/* Faturamento Card */}
              <div className="p-3 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-xl shadow-md flex flex-col justify-between h-24 col-span-2">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-sky-400 tracking-wider">Faturamento Hoje</span>
                  <div className="p-1 rounded-lg bg-sky-500/10 text-sky-400">
                    <CurrencyDollar size={16} />
                  </div>
                </div>
                <div className="flex justify-between items-end">
                  <div className="text-2xl font-black text-white">{formatCurrency(faturamentoHoje)}</div>
                  <div className="text-[10px] text-slate-400">
                    Total declarado/prints
                  </div>
                </div>
              </div>

              {/* Combustível Card */}
              <div className="p-3 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-xl shadow-md flex flex-col justify-between h-24">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-pink-400 tracking-wider">Combustível</span>
                  <div className="p-1 rounded-lg bg-pink-500/10 text-pink-400">
                    <GasPump size={16} />
                  </div>
                </div>
                <div>
                  <div className="text-lg font-black text-white">{formatCurrency(totalCombustivelHoje)}</div>
                  <div className="text-[10px] text-slate-400">Despesa de Hoje</div>
                </div>
              </div>

              {/* Manutenção Card */}
              <div className="p-3 bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-900/30 rounded-xl shadow-md flex flex-col justify-between h-24">
                <div className="flex justify-between items-start">
                  <span className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider">Manutenção</span>
                  <div className="p-1 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <Wrench size={16} />
                  </div>
                </div>
                <div>
                  <div className="text-lg font-black text-white">{veiculosManutencao.length}</div>
                  <div className="text-[10px] text-slate-400">Carros na Oficina</div>
                </div>
              </div>
            </div>

            {/* Active Journeys Monitor */}
            <Card className="p-4 bg-slate-900/40 border-slate-800 rounded-xl">
              <h2 className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-1.5">
                <Users size={16} className="text-sky-400" />
                Motoristas Operando ({activeJourneys.length})
              </h2>

              {activeJourneys.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  Nenhum motorista com jornada aberta no momento.
                </div>
              ) : (
                <div className="space-y-3">
                  {activeJourneys.map((j) => (
                    <div 
                      key={j.id} 
                      className="p-3 bg-slate-900/70 border border-slate-800 rounded-lg flex items-center justify-between gap-2"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-xs text-white truncate">
                            {j.motorista_nome || 'Sem nome'}
                          </span>
                          <Badge 
                            variant="outline" 
                            className={`px-1.5 py-0 text-[9px] uppercase tracking-wider ${
                              j.status === 'EM_ANDAMENTO' || j.status === 'ABERTA'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            }`}
                          >
                            {j.status === 'EM_ANDAMENTO' || j.status === 'ABERTA' ? 'Rodando' : 'Pausa'}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1">
                          <Car size={12} className="text-slate-500" />
                          Veículo: <strong className="text-slate-300">{j.veiculo_id}</strong>
                          {j.km?.inicial !== undefined && (
                            <span className="text-[9px] text-slate-500">
                              (KM Inicial: {j.km.inicial})
                            </span>
                          )}
                        </p>
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-black text-slate-200 block">
                          {formatCurrency(j.faturamento?.total_dia ?? 0)}
                        </span>
                        <span className="text-[9px] text-slate-500 block">
                          Faturado
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Maintenance Vehicles List */}
            <Card className="p-4 bg-slate-900/40 border-slate-800 rounded-xl">
              <h2 className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-1.5">
                <Wrench size={16} className="text-indigo-400" />
                Veículos em Manutenção ({veiculosManutencao.length})
              </h2>

              {veiculosManutencao.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">
                  Nenhum veículo em manutenção no momento.
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-2.5">
                  {veiculosManutencao.map((v) => (
                    <div 
                      key={v.id} 
                      className="p-3 bg-slate-900/70 border border-slate-800 rounded-lg flex items-center justify-between"
                    >
                      <div>
                        <span className="font-bold text-xs text-white block">
                          {v.id}
                        </span>
                        <span className="text-[10px] text-slate-400 mt-0.5 block">
                          {v.marca_modelo} ({v.cor})
                        </span>
                      </div>
                      <Badge className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 text-[9px] uppercase font-semibold">
                        Oficina
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
