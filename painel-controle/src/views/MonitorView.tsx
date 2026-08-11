import { useState, useEffect, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import type { Jornada, Veiculo, BaseOperacao } from '@/lib/types';
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
  Sparkle,
  Play,
  Crosshair,
  MapTrifold
} from '@phosphor-icons/react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { LiveMapView } from '@/components/LiveMapView';
import { DriverReplayOverlay, TelemetriaPoint } from '@/components/DriverReplayOverlay';

interface AlertaInatividade {
  motorista_id: string;
  motorista_nome: string;
  jornada_id: string;
  minutos_parado: number;
  ultima_posicao?: string;
  timestamp?: string;
}

function MotoristaMonitorRow({ 
  initialJornada, 
  formatCurrency,
  isFocado,
  onSelect,
  onShowCompleteRoute,
  onStartReplay
}: { 
  initialJornada: Jornada; 
  formatCurrency: (v: number) => string;
  isFocado?: boolean;
  onSelect?: (jornada: Jornada) => void;
  onShowCompleteRoute?: (jornada: Jornada) => void;
  onStartReplay?: (jornada: Jornada) => void;
}) {
  const isRodandoInicial = initialJornada.status === 'EM_ANDAMENTO' || initialJornada.status === 'ABERTA';
  const jId = initialJornada.id || (initialJornada as any)._id;

  // Polling de 5s ISOLADO apenas neste componente do motorista se a jornada estiver aberta/rodando
  const { data: jornada = initialJornada } = useQuery<Jornada>({
    queryKey: ['jornada-item-live', jId],
    queryFn: async () => {
      const { data } = await api.get<Jornada>(`/jornadas/${jId}`);
      return data;
    },
    enabled: isRodandoInicial && !!jId,
    refetchInterval: isRodandoInicial ? 5000 : false,
    initialData: initialJornada,
  });

  const isRodando = jornada.status === 'EM_ANDAMENTO' || jornada.status === 'ABERTA';
  const isEncerrada = jornada.status === 'ENCERRADA';
  const isParado = jornada.telemetria_status === 'PARADO';

  return (
    <div 
      className={`p-3.5 bg-slate-900/80 border rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all duration-200 shadow-sm ${
        isFocado ? 'border-sky-500 shadow-lg shadow-sky-500/20 bg-slate-900' : 'border-slate-800 hover:border-slate-700'
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-sm text-white tracking-wide truncate">
            {jornada.motorista_nome || 'Motorista'}
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
          {isRodando && jornada.telemetria_status && (
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

          {isRodando && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              LIVE 5s
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400 mt-2 font-mono flex-wrap">
          <span className="flex items-center gap-1 text-slate-300">
            <Car size={14} className="text-slate-500" />
            Placa: <strong className="text-sky-400 font-semibold">{jornada.veiculo_id}</strong>
          </span>
          {jornada.km?.inicial !== undefined && (
            <span className="text-slate-500">
              KM Inicial: {jornada.km.inicial}
            </span>
          )}
        </div>
      </div>

      {/* Action Buttons & Revenue */}
      <div className="flex items-center gap-3 border-t sm:border-t-0 border-slate-800/80 pt-2 sm:pt-0 shrink-0 justify-between sm:justify-end">
        {/* Actions */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => onSelect && onSelect(jornada)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 border transition-all ${
              isFocado
                ? 'bg-sky-500 text-white border-sky-400 shadow-md shadow-sky-500/30'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
            title="Centralizar Câmera do Mapa neste Motorista"
          >
            <Crosshair size={14} className={isFocado ? 'animate-pulse' : ''} />
            <span>{isFocado ? 'Focado' : 'Focar'}</span>
          </button>

          <button
            onClick={() => onShowCompleteRoute && onShowCompleteRoute(jornada)}
            className="px-2.5 py-1.5 rounded-lg bg-sky-900/40 hover:bg-sky-800/60 text-cyan-300 border border-cyan-500/40 text-xs font-bold flex items-center gap-1 transition-all"
            title="Exibir a Rota Completa Enquadrada no Mapa"
          >
            <MapTrifold size={14} className="text-cyan-400" />
            <span>Ver Rota Completa</span>
          </button>

          <button
            onClick={() => onStartReplay && onStartReplay(jornada)}
            className="px-2.5 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 text-xs font-bold flex items-center gap-1 transition-all shadow-sm"
            title="Refazer o Trajeto em Tempo Real com Animação"
          >
            <Play size={14} weight="fill" />
            <span>Refazer Trajeto</span>
          </button>
        </div>

        {/* Revenue Badge */}
        <div className="text-right">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-mono">
            Faturado Hoje
          </span>
          <span className="text-base font-black text-emerald-400 font-mono">
            {formatCurrency(jornada.faturamento?.total_dia ?? 0)}
          </span>
          <div className="flex justify-end gap-1 text-[9px] mt-0.5">
            {(jornada.faturamento?.uber ?? 0) > 0 && (
              <span className="bg-slate-900 text-white px-1.5 py-0.2 rounded font-semibold">
                Uber: R${jornada.faturamento?.uber}
              </span>
            )}
            {(jornada.faturamento?.noventa_nove ?? 0) > 0 && (
              <span className="bg-amber-500 text-slate-950 px-1.5 py-0.2 rounded font-bold">
                99: R${jornada.faturamento?.noventa_nove}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function MonitorView() {
  const [hoje, setHoje] = useState('');
  const [currentTimeStr, setCurrentTimeStr] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(() => {
    return localStorage.getItem('pwa_notifications_enabled') === 'true';
  });
  const [notifiedAlertKeys, setNotifiedAlertKeys] = useState<Set<string>>(new Set());

  // Focus & Replay State
  const [selectedJornadaId, setSelectedJornadaId] = useState<string | null>(null);
  const [replayJornada, setReplayJornada] = useState<Jornada | null>(null);
  const [replayPoints, setReplayPoints] = useState<TelemetriaPoint[]>([]);
  const [osrmRouteCoords, setOsrmRouteCoords] = useState<[number, number][]>([]);
  const [currentReplayIndex, setCurrentReplayIndex] = useState<number>(0);
  const [isPlayingReplay, setIsPlayingReplay] = useState<boolean>(false);
  const [replaySpeed, setReplaySpeed] = useState<number>(5);
  const [followVehicle, setFollowVehicle] = useState<boolean>(true);
  const [distanciaOsrmKm, setDistanciaOsrmKm] = useState<number>(0);
  const [distanciaGpsKm, setDistanciaGpsKm] = useState<number>(0);
  const [loadingReplay, setLoadingReplay] = useState<boolean>(false);
  const [telemetriaSearch, setTelemetriaSearch] = useState<string>('');

  const filteredReplayPoints = useMemo(() => {
    if (!telemetriaSearch) return replayPoints;
    const q = telemetriaSearch.toLowerCase();
    return replayPoints.filter(pt => 
      (pt.rua && pt.rua.toLowerCase().includes(q)) ||
      pt.status?.toLowerCase().includes(q) ||
      (pt.timestamp && pt.timestamp.includes(q))
    );
  }, [replayPoints, telemetriaSearch]);


  const replayTimerRef = useRef<any>(null);

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
    refetchInterval: 15000,
  });

  // Detect URL parameter ?jornada_id=... to auto-focus and auto-replay driver
  useEffect(() => {
    if (jornadas.length === 0) return;
    const hash = window.location.hash;
    if (hash.includes('jornada_id=')) {
      const jIdParam = hash.split('jornada_id=')[1]?.split('&')[0];
      if (jIdParam) {
        setSelectedJornadaId(jIdParam);
        const targetJ = jornadas.find((j) => (j.id || (j as any)._id) === jIdParam);
        if (targetJ && !replayJornada) {
          handleStartReplay(targetJ, true);
        }
      }
    }
  }, [jornadas, replayJornada]);

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

  // Real-Time SSE
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

  const { data: bases = [] } = useQuery<BaseOperacao[]>({
    queryKey: ['config-bases-operacoes'],
    queryFn: async () => {
      const { data } = await api.get<BaseOperacao[]>('/config/bases');
      return data;
    },
  });

  const [baseFocoId, setBaseFocoId] = useState<string>('AUTO');
  const selectedBase = bases.find((b) => b.id === baseFocoId) || null;

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

  // Trigger Push Notification for Alerts
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

  // Trigger Replay / Complete Route for Driver
  const handleStartReplay = async (jornada: Jornada, autoPlay: boolean = true) => {
    const motoristaId = (jornada as any).motorista_id || jornada.id;
    const jId = jornada.id || (jornada as any)._id;

    setLoadingReplay(true);
    toast.info(`Carregando rota de ${jornada.motorista_nome || 'Motorista'}...`);

    try {
      // 1. Fetch raw telemetry from Backend API
      const mId = typeof motoristaId === 'object' ? (motoristaId as any).$oid || motoristaId : motoristaId;
      const res = await api.get<any[]>(`/gps/motorista/${mId}`, {
        params: { jornada_id: jId, limite: 10000 }
      });

      const docs = res.data || [];
      if (docs.length === 0) {
        toast.warning(`Nenhum ponto de telemetria encontrado para esta jornada.`);
        setLoadingReplay(false);
        return;
      }

      // Convert docs into TelemetriaPoint array sorted chronologically
      const points: TelemetriaPoint[] = docs.map((d) => {
        let lat = 0;
        let lng = 0;
        if (d.localizacao?.coordinates) {
          lng = d.localizacao.coordinates[0];
          lat = d.localizacao.coordinates[1];
        } else if (d.localizacao?.lat && d.localizacao?.lon) {
          lat = Number(d.localizacao.lat);
          lng = Number(d.localizacao.lon);
        }

        return {
          id: d._id || d.id,
          timestamp: typeof d.timestamp === 'string' ? d.timestamp : new Date(d.timestamp).toISOString(),
          lat,
          lng,
          distancia_ultima_m: d.distancia_ultima_m || 0,
          status: d.status || 'CONDUZINDO',
          rua: d.rua || '',
        };
      }).filter(p => p.lat !== 0 && p.lng !== 0);

      points.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      if (points.length === 0) {
        toast.warning(`Pontos de GPS inválidos ou vazios.`);
        setLoadingReplay(false);
        return;
      }

      // Calculate Total GPS Distance
      let totalGpsM = 0;
      points.forEach(p => { totalGpsM += (p.distancia_ultima_m || 0); });
      setDistanciaGpsKm(totalGpsM / 1000);

      // 2. Fetch Local OSRM Map-Matching Route
      let osrmCoords: [number, number][] = [];
      let osrmDistM = 0;

      try {
        const sampled: TelemetriaPoint[] = [];
        for (let i = 0; i < points.length; i += 4) {
          sampled.push(points[i]);
        }

        if (sampled[sampled.length - 1] !== points[points.length - 1]) {
          sampled.push(points[points.length - 1]);
        }

        const chunkSize = 50;
        for (let i = 0; i < sampled.length - 1; i += chunkSize) {
          const chunk = sampled.slice(i, i + chunkSize + 1);
          const coordsStr = chunk.map(p => `${p.lng},${p.lat}`).join(';');
          
          const osrmUrl = `http://localhost:5000/route/v1/driving/${coordsStr}?overview=full&geometries=geojson`;
          const osrmRes = await fetch(osrmUrl);
          
          if (osrmRes.ok) {
            const data = await osrmRes.json();
            if (data.code === 'Ok' && data.routes && data.routes.length > 0) {
              const r = data.routes[0];
              osrmDistM += r.distance;
              const coords = r.geometry.coordinates.map((c: any) => [c[1], c[0]] as [number, number]);
              osrmCoords.push(...coords);
            }
          }
        }
      } catch (err) {
        console.warn('OSRM local não disponível no momento para o painel:', err);
      }

      setOsrmRouteCoords(osrmCoords);
      setDistanciaOsrmKm(osrmDistM > 0 ? osrmDistM / 1000 : totalGpsM / 1000);
      setReplayPoints(points);
      setReplayJornada(jornada);
      setCurrentReplayIndex(0);
      setIsPlayingReplay(autoPlay);
      setFollowVehicle(autoPlay);
      setLoadingReplay(false);

      if (autoPlay) {
        toast.success(`Iniciando Replay de ${jornada.motorista_nome || 'Motorista'} (${points.length} pontos GPS)!`);
      } else {
        toast.success(`Exibindo Rota Completa de ${jornada.motorista_nome || 'Motorista'}! Clique em "Refazer Caminho" para animar.`);
      }
    } catch (err) {
      console.error('Erro ao buscar rota do motorista:', err);
      toast.error('Erro ao buscar dados de telemetria do motorista.');
      setLoadingReplay(false);
    }
  };

  const handleShowCompleteRoute = (jornada: Jornada) => {
    handleStartReplay(jornada, false);
  };

  // Replay Animation Timer Loop
  useEffect(() => {
    if (!isPlayingReplay || replayPoints.length === 0) {
      if (replayTimerRef.current) clearInterval(replayTimerRef.current);
      return;
    }

    const intervalMs = Math.max(30, Math.round(500 / replaySpeed));
    replayTimerRef.current = setInterval(() => {
      setCurrentReplayIndex((prev) => {
        if (prev < replayPoints.length - 1) {
          return prev + 1;
        } else {
          setIsPlayingReplay(false);
          return prev;
        }
      });
    }, intervalMs);

    return () => {
      if (replayTimerRef.current) clearInterval(replayTimerRef.current);
    };
  }, [isPlayingReplay, replayPoints.length, replaySpeed]);

  const handleCloseReplay = () => {
    setIsPlayingReplay(false);
    setReplayJornada(null);
    setReplayPoints([]);
    setOsrmRouteCoords([]);
    setCurrentReplayIndex(0);
  };

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

            {/* Live Map View Section with Replay Overlay */}
            <div className="space-y-3 relative">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
                  <span>🗺️ Mapa Ao Vivo da Frota & Replay de Trajeto</span>
                  <Badge 
                    variant="outline" 
                    className={replayJornada ? 'bg-sky-500/20 border-sky-500/40 text-sky-300 font-mono' : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 text-[10px]'}
                  >
                    {replayJornada ? 'ROTA / REPLAY ATIVO (OSRM)' : 'SSE ONLINE'}
                  </Badge>
                </h2>

                <div className="flex items-center gap-3 flex-wrap">
                  {/* Seletor de Base de Operações */}
                  <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl text-xs">
                    <span className="text-slate-400 font-medium">🏢 Base Central:</span>
                    <select
                      value={baseFocoId}
                      onChange={(e) => setBaseFocoId(e.target.value)}
                      className="bg-slate-800 border border-slate-700 text-xs text-white rounded px-2 py-0.5 font-medium focus:outline-none focus:border-sky-500"
                    >
                      <option value="AUTO">🎯 Automático (Principal / Frota)</option>
                      {bases.map((b) => (
                        <option key={b.id} value={b.id}>
                          🏢 {b.nome} {b.is_principal ? '★ (Principal)' : ''}
                        </option>
                      ))}
                    </select>
                  </div>

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
              </div>

              {/* Replay Player Overlay ABOVE the Map */}
              {replayJornada && (
                <DriverReplayOverlay
                  jornada={replayJornada}
                  telemetriaPoints={replayPoints}
                  currentIndex={currentReplayIndex}
                  isPlaying={isPlayingReplay}
                  speed={replaySpeed}
                  followVehicle={followVehicle}
                  distanciaOsrmKm={distanciaOsrmKm}
                  distanciaGpsKm={distanciaGpsKm}
                  onIndexChange={(idx) => setCurrentReplayIndex(idx)}
                  onTogglePlay={() => setIsPlayingReplay(!isPlayingReplay)}
                  onRestart={() => setCurrentReplayIndex(0)}
                  onToggleFollow={() => setFollowVehicle(!followVehicle)}
                  onFitCompleteRoute={() => setFollowVehicle(false)}
                  onSpeedChange={(spd) => setReplaySpeed(spd)}
                  onClose={handleCloseReplay}
                />
              )}

              {/* Grid with Interactive Telemetry Sidebar + Map Component */}
              {replayJornada ? (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                  {/* Interactive Telemetry List Sidebar */}
                  <Card className="lg:col-span-4 p-4 bg-[#0d1117]/95 border-slate-800 rounded-2xl shadow-xl flex flex-col h-[520px]">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
                        <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                          Pontos de Telemetria ({replayPoints.length})
                        </h3>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400">Clique para pular</span>
                    </div>

                    <div className="mb-3">
                      <input
                        type="text"
                        placeholder="Filtrar por rua ou horário..."
                        value={telemetriaSearch}
                        onChange={(e) => setTelemetriaSearch(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
                      />
                    </div>

                    <div className="flex-1 overflow-y-auto pr-1 space-y-2">
                      {filteredReplayPoints.length === 0 ? (
                        <div className="text-center py-10 text-slate-500 text-xs">
                          Nenhum ponto encontrado com o filtro aplicado.
                        </div>
                      ) : (
                        filteredReplayPoints.map((pt) => {
                          const realIdx = replayPoints.findIndex((p) => p.timestamp === pt.timestamp && p.lat === pt.lat);
                          const isSelected = realIdx === currentReplayIndex;
                          const isParado = pt.status === 'PARADO';
                          let cleanedTs = String(pt.timestamp || '').trim().replace(' ', 'T');
                          if (cleanedTs && !cleanedTs.endsWith('Z') && !/[+-]\d{2}:?\d{2}$/.test(cleanedTs)) {
                            cleanedTs += 'Z';
                          }
                          const timeOnly = cleanedTs ? new Date(cleanedTs).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--';

                          return (
                            <div
                              key={pt.id || realIdx}
                              onClick={() => {
                                if (realIdx !== -1) {
                                  setCurrentReplayIndex(realIdx);
                                  setIsPlayingReplay(false);
                                }
                              }}
                              className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all ${
                                isSelected
                                  ? 'bg-sky-950/90 border-sky-400 shadow-md shadow-sky-950/50'
                                  : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono font-bold text-sky-300 text-[11px]">{timeOnly}</span>
                                <Badge 
                                  variant="outline" 
                                  className={`text-[9px] font-mono font-bold uppercase ${
                                    isParado 
                                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' 
                                      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                                  }`}
                                >
                                  {pt.status || 'CONDUZINDO'}
                                </Badge>
                              </div>

                              <div className="text-[11px] text-slate-300 truncate font-medium flex items-center gap-1">
                                <span className="text-slate-500">📍</span>
                                <span className="truncate">{pt.rua || 'Via não identificada'}</span>
                              </div>

                              {pt.distancia_ultima_m ? (
                                <div className="text-[10px] font-mono text-slate-500 mt-1 flex items-center justify-between">
                                  <span>+{(pt.distancia_ultima_m).toFixed(0)}m desde o anterior</span>
                                  <span>Point #{realIdx + 1}</span>
                                </div>
                              ) : null}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </Card>

                  {/* Live Map Component */}
                  <div className="lg:col-span-8">
                    <LiveMapView 
                      jornadas={displayedJornadas} 
                      bases={bases} 
                      baseFoco={selectedBase} 
                      selectedJornadaId={selectedJornadaId}
                      onSelectJornada={(j) => setSelectedJornadaId(j.id || (j as any)._id)}
                      onStartReplay={(j) => handleStartReplay(j, true)}
                      onShowCompleteRoute={handleShowCompleteRoute}
                      replayMode={!!replayJornada}
                      replayPoints={replayPoints}
                      osrmRouteCoords={osrmRouteCoords}
                      currentReplayIndex={currentReplayIndex}
                      followVehicle={followVehicle}
                    />
                  </div>
                </div>
              ) : (
                <LiveMapView 
                  jornadas={displayedJornadas} 
                  bases={bases} 
                  baseFoco={selectedBase} 
                  selectedJornadaId={selectedJornadaId}
                  onSelectJornada={(j) => setSelectedJornadaId(j.id || (j as any)._id)}
                  onStartReplay={(j) => handleStartReplay(j, true)}
                  onShowCompleteRoute={handleShowCompleteRoute}
                  replayMode={!!replayJornada}
                  replayPoints={replayPoints}
                  osrmRouteCoords={osrmRouteCoords}
                  currentReplayIndex={currentReplayIndex}
                  followVehicle={followVehicle}
                />
              )}


            </div>

            {/* Futuristic KPI Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
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

            {/* Secondary KPI Bar */}
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
                    const jIdStr = j.id || (j as any)._id;
                    const isFocado = selectedJornadaId === jIdStr;
                    return (
                      <MotoristaMonitorRow 
                        key={jIdStr} 
                        initialJornada={j} 
                        formatCurrency={formatCurrency}
                        isFocado={isFocado}
                        onSelect={(selected) => setSelectedJornadaId(selected.id || (selected as any)._id)}
                        onShowCompleteRoute={handleShowCompleteRoute}
                        onStartReplay={(selected) => handleStartReplay(selected, true)}
                      />
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
