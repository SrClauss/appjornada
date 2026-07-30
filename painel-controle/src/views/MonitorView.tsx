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
  Circle,
  BellRinging,
  BellSlash,
  WarningOctagon,
  Gauge,
  Sparkle
} from '@phosphor-icons/react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { LiveMapView } from '@/components/LiveMapView';

interface AlertaInatividade {
  motorista_id: string;
  motorista_nome: string;
  jornada_id: string;
  minutos_parado: number;
  ultima_posicao?: string;
  timestamp?: string;
}

export function MonitorView() {
  const [hoje, setHoje] = useState('');
  const [currentTimeStr, setCurrentTimeStr] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(() => {
    return localStorage.getItem('pwa_notifications_enabled') === 'true';
  });
  const [notifiedAlertKeys, setNotifiedAlertKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      setHoje(`${yyyy}-${mm}-${dd}`);

      setCurrentTimeStr(
        now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      );
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
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
    refetchInterval: 10000,
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

  const { 
    data: alertasData,
    refetch: refetchAlertas,
    isRefetching: refetchingAlertas
  } = useQuery({
    queryKey: ['monitor-alertas-inatividade'],
    queryFn: async () => {
      const { data } = await api.get<{ alertas: AlertaInatividade[]; total_alertas: number }>('/gps/alertas-inatividade');
      return data;
    },
    refetchInterval: 10000,
  });

  const alertas = alertasData?.alertas ?? [];

  // Real-Time SSE (Server-Sent Events) - Transmissão sem necessidade de Polling constante
  useEffect(() => {
    const sseUrl = `${api.defaults.baseURL || ''}/events/stream`;
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(sseUrl);
      eventSource.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          if (payload.type !== 'ping') {
            refetchJornadas();
            refetchVeiculos();
            refetchAlertas();
          }
        } catch (e) {
          // Ignore
        }
      };
    } catch (e) {
      console.warn('SSE EventSource indisponível:', e);
    }
    return () => {
      if (eventSource) eventSource.close();
    };
  }, [refetchJornadas, refetchVeiculos, refetchAlertas]);

  // Gestão da Configuração do Limite de KM Morta pelo Gestor
  const { data: configInatividade, refetch: refetchConfig } = useQuery({
    queryKey: ['config-inatividade'],
    queryFn: async () => {
      const { data } = await api.get<{ tempo_inatividade_minutos: number; raio_mudanca_metros: number; limite_km_morta_pct: number }>('/config/inatividade');
      return data;
    },
  });

  const [limiteKmMortaInput, setLimiteKmMortaInput] = useState<number>(20);

  useEffect(() => {
    if (configInatividade?.limite_km_morta_pct !== undefined) {
      setLimiteKmMortaInput(configInatividade.limite_km_morta_pct);
    }
  }, [configInatividade]);

  const handleSalvarLimiteKmMorta = async () => {
    try {
      await api.put('/config/inatividade', {
        tempo_inatividade_minutos: configInatividade?.tempo_inatividade_minutos ?? 25,
        raio_mudanca_metros: configInatividade?.raio_mudanca_metros ?? 30,
        limite_km_morta_pct: Number(limiteKmMortaInput),
      });
      toast.success(`Limite de Razão KM Morta atualizado para ${limiteKmMortaInput}%!`);
      refetchConfig();
      refetchJornadas();
    } catch (e) {
      toast.error('Erro ao atualizar limite de auditoria.');
    }
  };

  // Dispara Notificação Push do Navegador quando surge novo alerta
  useEffect(() => {
    if (!notificationsEnabled || Notification.permission !== 'granted' || alertas.length === 0) {
      return;
    }

    const newKeys = new Set(notifiedAlertKeys);
    let newlyNotified = false;

    for (const alerta of alertas) {
      const alertKey = `${alerta.jornada_id}_${alerta.minutos_parado}`;
      if (!newKeys.has(alertKey)) {
        newKeys.add(alertKey);
        newlyNotified = true;

        try {
          new Notification('🚨 Alerta de Inatividade', {
            body: `Motorista ${alerta.motorista_nome} está inativo há ${alerta.minutos_parado} min!`,
            icon: '/favicon.ico',
            tag: `inatividade_${alerta.jornada_id}`,
          });
        } catch (err) {
          console.error('Erro ao emitir notificação de inatividade:', err);
        }
      }
    }

    if (newlyNotified) {
      setNotifiedAlertKeys(newKeys);
    }
  }, [alertas, notificationsEnabled, notifiedAlertKeys]);

  const toggleNotifications = async () => {
    if (!notificationsEnabled) {
      if (!('Notification' in window)) {
        toast.error('Este navegador não possui suporte a Notificações Push.');
        return;
      }

      let permission = Notification.permission;
      if (permission === 'default') {
        permission = await Notification.requestPermission();
      }

      if (permission === 'granted') {
        setNotificationsEnabled(true);
        localStorage.setItem('pwa_notifications_enabled', 'true');
        toast.success('Notificações de Inatividade ativadas em tempo real!');

        try {
          new Notification('📢 Monitor PWA', {
            body: 'Notificações de inatividade em tempo real foram ativadas com sucesso.',
            icon: '/favicon.ico',
          });
        } catch (e) {
          console.error('Erro ao emitir notificação de teste:', e);
        }
      } else {
        toast.error('Permissão de notificação negada no navegador.');
      }
    } else {
      setNotificationsEnabled(false);
      localStorage.setItem('pwa_notifications_enabled', 'false');
      toast.info('Notificações de inatividade desativadas.');
    }
  };

  const handleManualRefresh = () => {
    refetchJornadas();
    refetchVeiculos();
    refetchAlertas();
  };

  const handleGoBack = () => {
    window.location.hash = '/dashboard';
  };

  const [filtroStatus, setFiltroStatus] = useState<'ATIVAS' | 'TODAS' | 'ENCERRADAS'>('ATIVAS');

  // KPI Calculations
  const activeJourneys = jornadas.filter(
    (j) => j.status === 'ABERTA' || j.status === 'EM_ANDAMENTO' || j.status === 'EM_PAUSA'
  );

  const displayedJornadas = jornadas.filter((j) => {
    if (filtroStatus === 'ATIVAS') {
      return j.status === 'ABERTA' || j.status === 'EM_ANDAMENTO' || j.status === 'EM_PAUSA';
    }
    if (filtroStatus === 'ENCERRADAS') {
      return j.status === 'ENCERRADA';
    }
    return true;
  });
  
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

  let totalDespesasHoje = 0;
  let lucroLiquidoHoje = 0;
  for (const j of jornadas) {
    if (j.dre?.lucro_liquido) {
      lucroLiquidoHoje += j.dre.lucro_liquido;
    }
    for (const ab of (j.abastecimentos ?? [])) {
      totalDespesasHoje += (ab.valor_gasolina ?? ab.gasolina ?? 0) + (ab.valor_gnv ?? ab.gnv ?? 0) + (ab.valor_etanol ?? ab.etanol ?? 0)
        + (ab.valor_pedagio ?? 0) + (ab.valor_estacionamento ?? 0) + (ab.valor_outros ?? 0);
    }
  }

  const veiculosManutencao = veiculos.filter(
    (v) => v.situacao === 'MANUTENCAO'
  );

  const formatCurrency = (v: number) =>
    v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

  const isGlobalLoading = loadingJornadas || loadingVeiculos;
  const isGlobalRefetching = refetchingJornadas || refetchingVeiculos || refetchingAlertas;

  return (
    <div className="flex flex-col min-h-screen bg-[#07090e] text-slate-100 antialiased font-sans selection:bg-cyan-500 selection:text-black">
      {/* Background Subtle Glow Grid */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-sky-900/10 via-[#07090e] to-[#07090e] pointer-events-none z-0"></div>

      {/* Futuristic Header */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-4 py-3 bg-[#0d1117]/85 backdrop-blur-xl border-b border-slate-800/80 shadow-2xl">
        <div className="flex items-center gap-3">
          <button 
            onClick={handleGoBack}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 hover:text-white border border-slate-700/50 transition-all duration-200 shadow-sm group"
            title="Voltar ao Painel"
          >
            <ArrowLeft size={18} className="group-hover:-translate-x-0.5 transition-transform" />
          </button>
          
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Gauge size={18} className="text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                  Monitor Operacional
                </h1>
                <Badge variant="outline" className="bg-sky-500/10 border-sky-500/30 text-sky-400 text-[10px] px-1.5 py-0 font-mono">
                  LIVE
                </Badge>
              </div>
              <p className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                <span>{currentTimeStr}</span>
                <span className="text-slate-600">•</span>
                <span>Torre de Controle</span>
              </p>
            </div>
          </div>
        </div>

        {/* Control Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Notification Toggle Button */}
          <button
            onClick={toggleNotifications}
            title={notificationsEnabled ? "Notificações de inatividade ativas" : "Clique para ativar notificações de inatividade"}
            className={`px-3 py-1.5 rounded-xl transition-all duration-300 flex items-center gap-1.5 text-xs font-semibold border backdrop-blur-md shadow-sm ${
              notificationsEnabled
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25 shadow-emerald-950/40'
                : 'bg-slate-800/80 border-slate-700/80 text-slate-400 hover:bg-slate-700/80 hover:text-slate-200'
            }`}
          >
            {notificationsEnabled ? (
              <>
                <BellRinging size={16} className="text-emerald-400 animate-pulse" />
                <span className="hidden sm:inline">Alertas ON</span>
              </>
            ) : (
              <>
                <BellSlash size={16} />
                <span className="hidden sm:inline">Alertas OFF</span>
              </>
            )}
          </button>

          {/* Refresh Button */}
          <button
            onClick={handleManualRefresh}
            disabled={isGlobalLoading}
            className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/80 disabled:opacity-50 text-slate-300 hover:text-white transition-all duration-200 flex items-center gap-1.5 text-xs font-medium shadow-sm"
            title="Atualizar Dados"
          >
            <ArrowClockwise size={15} className={`text-sky-400 ${isGlobalRefetching ? 'animate-spin' : ''}`} />
            <span className="hidden md:inline">{isGlobalRefetching ? 'Atualizando...' : 'Atualizar'}</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-1 p-4 md:p-6 space-y-6 max-w-7xl mx-auto w-full">
        {isGlobalLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-28 w-full bg-slate-900/60 rounded-2xl border border-slate-800/50" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Skeleton className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800/50" />
              <Skeleton className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800/50" />
              <Skeleton className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800/50" />
              <Skeleton className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800/50" />
            </div>
            <Skeleton className="h-64 w-full bg-slate-900/60 rounded-2xl border border-slate-800/50" />
          </div>
        ) : (
          <>
            {/* Critical Alert Banner for Inactivity */}
            {alertas.length > 0 && (
              <Card className="p-4 bg-gradient-to-r from-rose-950/70 via-rose-900/40 to-slate-900/80 border-rose-600/50 rounded-2xl shadow-xl shadow-rose-950/30 backdrop-blur-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full blur-2xl pointer-events-none"></div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30">
                      <WarningOctagon size={20} className="animate-pulse" />
                    </div>
                    <div>
                      <h2 className="text-sm font-bold text-rose-200 tracking-wide flex items-center gap-2">
                        Alertas de Inatividade Detectados
                        <Badge className="bg-rose-500/30 text-rose-200 border-rose-400/40 font-mono text-[10px] px-2">
                          {alertas.length} {alertas.length === 1 ? 'ALERTA' : 'ALERTAS'}
                        </Badge>
                      </h2>
                      <p className="text-xs text-rose-300/80 mt-0.5">Motoristas sem deslocamento superior ao raio configurado</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {alertas.map((a) => (
                    <div 
                      key={a.jornada_id} 
                      className="p-3 bg-[#0d1117]/90 border border-rose-500/30 rounded-xl flex items-center justify-between gap-3 text-xs shadow-inner"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm truncate">{a.motorista_nome}</span>
                          <span className="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono font-semibold text-[10px] shrink-0">
                            ⏱️ {a.minutos_parado} min parado
                          </span>
                        </div>
                        {a.ultima_posicao && (
                          <p className="text-[11px] text-slate-400 mt-1 truncate flex items-center gap-1">
                            <span className="text-rose-400 font-bold">📍</span> {a.ultima_posicao}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Live Map View Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                  <span>🗺️ Mapa Ao Vivo da Frota em Tempo Real</span>
                  <Badge variant="outline" className="bg-emerald-500/10 border-emerald-500/30 text-emerald-400 text-[10px]">
                    SSE ONLINE
                  </Badge>
                </h2>

                {/* Gestor KM Morta Config Bar */}
                <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl text-xs">
                  <span className="text-slate-400 font-medium">Limite Razão KM Morta:</span>
                  <input
                    type="number"
                    value={limiteKmMortaInput}
                    onChange={(e) => setLimiteKmMortaInput(Number(e.target.value))}
                    className="w-16 bg-slate-800 border border-slate-700 text-white font-mono text-center rounded px-1 py-0.5"
                    min="0"
                    max="100"
                  />
                  <span className="text-slate-400">%</span>
                  <button
                    onClick={handleSalvarLimiteKmMorta}
                    className="ml-1 bg-sky-600 hover:bg-sky-500 text-white px-2 py-0.5 rounded text-[11px] font-bold transition-all"
                  >
                    Salvar
                  </button>
                </div>
              </div>

              <LiveMapView jornadas={displayedJornadas} />
            </div>

            {/* Futuristic KPI Grid (4 Cols on Desktop, 2 Cols on Mobile) */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
              
              {/* Rodando Card */}
              <div className="p-4 bg-gradient-to-br from-emerald-950/30 via-slate-900/80 to-slate-950 border border-emerald-500/30 rounded-2xl shadow-xl shadow-emerald-950/20 backdrop-blur-md flex flex-col justify-between h-28 relative overflow-hidden group hover:border-emerald-500/50 transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-xl pointer-events-none group-hover:bg-emerald-500/20 transition-all"></div>
                <div className="flex justify-between items-start">
                  <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider font-mono">Motoristas Rodando</span>
                  <div className="p-1.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 shadow-sm">
                    <Circle weight="fill" size={12} className="animate-pulse" />
                  </div>
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <div className="text-3xl font-black text-white tracking-tight font-mono">{motoristasAndando}</div>
                  <span className="text-[10px] text-emerald-400/80 font-medium">Em trânsito</span>
                </div>
              </div>

              {/* Pausa Card */}
              <div className="p-4 bg-gradient-to-br from-amber-950/30 via-slate-900/80 to-slate-950 border border-amber-500/30 rounded-2xl shadow-xl shadow-amber-950/20 backdrop-blur-md flex flex-col justify-between h-28 relative overflow-hidden group hover:border-amber-500/50 transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full blur-xl pointer-events-none group-hover:bg-amber-500/20 transition-all"></div>
                <div className="flex justify-between items-start">
                  <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider font-mono">Em Pausa</span>
                  <div className="p-1.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shadow-sm">
                    <Clock size={16} />
                  </div>
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <div className="text-3xl font-black text-white tracking-tight font-mono">{motoristasPausa}</div>
                  <span className="text-[10px] text-amber-400/80 font-medium">Em intervalo</span>
                </div>
              </div>

              {/* Faturamento Card */}
              <div className="p-4 bg-gradient-to-br from-sky-950/30 via-slate-900/80 to-slate-950 border border-sky-500/30 rounded-2xl shadow-xl shadow-sky-950/20 backdrop-blur-md flex flex-col justify-between h-28 relative overflow-hidden group hover:border-sky-500/50 transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-sky-500/10 rounded-full blur-xl pointer-events-none group-hover:bg-sky-500/20 transition-all"></div>
                <div className="flex justify-between items-start">
                  <span className="text-[11px] font-bold text-sky-400 uppercase tracking-wider font-mono">Faturamento Hoje</span>
                  <div className="p-1.5 rounded-xl bg-sky-500/15 border border-sky-500/30 text-sky-400 shadow-sm">
                    <CurrencyDollar size={16} />
                  </div>
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <div className="text-2xl md:text-3xl font-black text-white tracking-tight font-mono">{formatCurrency(faturamentoHoje)}</div>
                </div>
              </div>

              {/* Lucro Líquido Real Card */}
              <div className="p-4 bg-gradient-to-br from-indigo-950/30 via-slate-900/80 to-slate-950 border border-indigo-500/30 rounded-2xl shadow-xl shadow-indigo-950/20 backdrop-blur-md flex flex-col justify-between h-28 relative overflow-hidden group hover:border-indigo-500/50 transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-indigo-500/10 rounded-full blur-xl pointer-events-none group-hover:bg-indigo-500/20 transition-all"></div>
                <div className="flex justify-between items-start">
                  <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider font-mono">Lucro Líquido Real</span>
                  <div className="p-1.5 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 shadow-sm">
                    <Sparkle size={16} />
                  </div>
                </div>
                <div className="flex items-baseline justify-between mt-2">
                  <div className="text-2xl md:text-3xl font-black text-white tracking-tight font-mono">{formatCurrency(lucroLiquidoHoje)}</div>
                  <span className="text-[10px] text-indigo-400/80 font-medium">DRE Líquido</span>
                </div>
              </div>

            </div>

            {/* Secondary KPI Bar (Despesas + Oficina) */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-pink-500/10 border border-pink-500/20 text-pink-400">
                    <GasPump size={16} />
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">Despesas do Dia</span>
                    <span className="text-sm font-bold text-white font-mono">{formatCurrency(totalDespesasHoje)}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400">
                    <Wrench size={16} />
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-slate-400 block font-mono">Na Oficina</span>
                    <span className="text-sm font-bold text-white font-mono">{veiculosManutencao.length} Veículos</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Journeys Monitor Card */}
            <Card className="p-5 bg-[#0d1117]/80 border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 border-b border-slate-800/80 pb-3">
                <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
                    <Users size={16} />
                  </div>
                  <span>Monitor de Jornadas ({displayedJornadas.length})</span>
                </h2>

                {/* Filter Selector Tabs */}
                <div className="flex items-center gap-1 bg-slate-900/90 border border-slate-800 p-1 rounded-xl text-xs">
                  <button
                    onClick={() => setFiltroStatus('ATIVAS')}
                    className={`px-3 py-1 rounded-lg font-bold transition-all text-[11px] ${
                      filtroStatus === 'ATIVAS'
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    🚀 Ativas ({activeJourneys.length})
                  </button>
                  <button
                    onClick={() => setFiltroStatus('TODAS')}
                    className={`px-3 py-1 rounded-lg font-bold transition-all text-[11px] ${
                      filtroStatus === 'TODAS'
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    📋 Todas ({jornadas.length})
                  </button>
                  <button
                    onClick={() => setFiltroStatus('ENCERRADAS')}
                    className={`px-3 py-1 rounded-lg font-bold transition-all text-[11px] ${
                      filtroStatus === 'ENCERRADAS'
                        ? 'bg-sky-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    🏁 Encerradas ({jornadas.length - activeJourneys.length})
                  </button>
                </div>
              </div>

              {displayedJornadas.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-xs flex flex-col items-center gap-2">
                  <Users size={32} className="text-slate-700" />
                  <span>Nenhuma jornada encontrada neste filtro.</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3">
                  {displayedJornadas.map((j) => {
                    const isRodando = j.status === 'EM_ANDAMENTO' || j.status === 'ABERTA';
                    const isEncerrada = j.status === 'ENCERRADA';
                    const isParado = j.telemetria_status === 'PARADO';

                    return (
                      <div 
                        key={j.id} 
                        className="p-3.5 bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all duration-200 shadow-sm"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-sm text-white tracking-wide truncate">
                              {j.motorista_nome || 'Motorista'}
                            </span>
                            
                            {/* Status Badge */}
                            <Badge 
                              variant="outline" 
                              className={`px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-md border ${
                                isEncerrada
                                  ? 'bg-slate-800 text-slate-400 border-slate-700'
                                  : isRodando
                                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                  : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              }`}
                            >
                              {isEncerrada ? 'ENCERRADA' : isRodando ? 'RODANDO' : 'EM PAUSA'}
                            </Badge>

                            {/* Telemetria Status Badge */}
                            {isRodando && j.telemetria_status && (
                              <Badge 
                                variant="outline" 
                                className={`px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-md border ${
                                  isParado
                                    ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
                                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                }`}
                              >
                                {isParado ? 'PARADO' : 'EM MOVIMENTO'}
                              </Badge>
                            )}
                          </div>

                          <div className="flex items-center gap-3 text-xs text-slate-400 mt-2 font-mono flex-wrap">
                            <span className="flex items-center gap-1 text-slate-300">
                              <Car size={14} className="text-slate-500" />
                              Placa: <strong className="text-sky-400 font-semibold">{j.veiculo_id}</strong>
                            </span>
                            {j.km?.inicial !== undefined && (
                              <span className="text-slate-500">
                                KM Inicial: {j.km.inicial}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Revenue Badge */}
                        <div className="text-left sm:text-right border-t sm:border-t-0 border-slate-800/80 pt-2 sm:pt-0 shrink-0">
                          <span className="text-xs text-slate-500 uppercase tracking-wider block font-mono">
                            Faturado Hoje
                          </span>
                          <span className="text-base font-black text-emerald-400 font-mono">
                            {formatCurrency(j.faturamento?.total_dia ?? 0)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>

            {/* Maintenance Vehicles Section */}
            {veiculosManutencao.length > 0 && (
              <Card className="p-5 bg-[#0d1117]/80 border-slate-800/90 rounded-2xl shadow-2xl backdrop-blur-xl">
                <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
                  <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      <Wrench size={16} />
                    </div>
                    Veículos em Manutenção ({veiculosManutencao.length})
                  </h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {veiculosManutencao.map((v) => (
                    <div 
                      key={v.id} 
                      className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center justify-between gap-2 text-xs"
                    >
                      <div>
                        <span className="font-bold text-white text-sm font-mono block">
                          {v.id}
                        </span>
                        <span className="text-slate-400 text-xs block mt-0.5">
                          {v.marca_modelo} ({v.cor || 'Sem cor'})
                        </span>
                      </div>
                      <Badge className="bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 px-2.5 py-1 text-[10px] uppercase font-bold font-mono">
                        OFICINA
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            )}

          </>
        )}
      </main>
    </div>
  );
}
