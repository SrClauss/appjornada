import { useState, useEffect, useRef, useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Eye, 
  ArrowLeft, 
  User, 
  Car, 
  Compass, 
  Coffee, 
  Drop, 
  Flag, 
  Clock, 
  MapTrifold, 
  UploadSimple, 
  FileArrowUp, 
  ShieldCheck, 
  Warning,
  ListBullets,
  Trash,
  Calendar,
  Camera
} from '@phosphor-icons/react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useQueryClient } from '@tanstack/react-query';
import { useJornadas } from '@/hooks/useJornadas';
import type { Jornada, JourneyStatus } from '@/lib/types';
import api from '@/lib/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapViewProps {
  coordinates: [number, number][];
  corridasParticulares?: any[];
}

function JourneyMap({ coordinates, corridasParticulares }: MapViewProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  const latLngs = coordinates.map((c) => [c[1], c[0]] as [number, number]);
  const base = latLngs[0];

  const segments: { coords: [number, number][]; direction: 'away' | 'towards' }[] = [];

  if (latLngs.length > 0) {
    let currentSegment: [number, number][] = [latLngs[0]];
    let lastDir: 'away' | 'towards' | null = null;

    for (let i = 1; i < latLngs.length; i++) {
      const prev = latLngs[i - 1];
      const curr = latLngs[i];

      const d_prev = Math.sqrt((prev[0] - base[0])**2 + (prev[1] - base[1])**2);
      const d_curr = Math.sqrt((curr[0] - base[0])**2 + (curr[1] - base[1])**2);

      const dir = d_curr >= d_prev ? 'away' : 'towards';

      if (lastDir !== null && dir !== lastDir) {
        currentSegment.push(curr);
        segments.push({ coords: currentSegment, direction: lastDir });
        currentSegment = [prev, curr];
      } else {
        currentSegment.push(curr);
      }
      lastDir = dir;
    }
    if (currentSegment.length > 1) {
      segments.push({ coords: currentSegment, direction: lastDir || 'away' });
    }
  }

  useEffect(() => {
    if (!mapContainerRef.current) return;

    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    });

    let centerPoint: [number, number] = [-20.3155, -40.2944];
    if (latLngs.length > 0) {
      centerPoint = latLngs[0];
    } else if (corridasParticulares && corridasParticulares.length > 0) {
      const firstCp = corridasParticulares[0];
      if (firstCp.localizacao_inicio?.lat && firstCp.localizacao_inicio?.lon) {
        centerPoint = [firstCp.localizacao_inicio.lat, firstCp.localizacao_inicio.lon];
      }
    }

    const map = L.map(mapContainerRef.current).setView(centerPoint, 13);
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    layerGroupRef.current = layerGroup;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [coordinates.length === 0, !corridasParticulares || corridasParticulares.length === 0]);

  useEffect(() => {
    const map = mapRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    let mainBounds: L.LatLngBounds | null = null;

    if (latLngs.length > 0) {
      const startIcon = L.divIcon({
        className: 'custom-marker-start',
        html: '<div style="background-color: #3b82f6; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      const endIcon = L.divIcon({
        className: 'custom-marker-end',
        html: '<div style="background-color: #ef4444; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });

      segments.forEach((seg) => {
        const color = seg.direction === 'away' ? '#3b82f6' : '#10b981';
        const name = seg.direction === 'away' ? 'Afastando-se da Base (Outbound)' : 'Aproximando-se da Base (Inbound)';
        
        const poly = L.polyline(seg.coords, {
          color,
          weight: 5,
          opacity: 0.85,
          lineJoin: 'round',
        }).addTo(layerGroup);

        poly.bindPopup(`<strong>Trecho: ${name}</strong>`);

        if (!mainBounds) {
          mainBounds = poly.getBounds();
        } else {
          mainBounds.extend(poly.getBounds());
        }
      });

      L.marker(latLngs[0], { icon: startIcon }).addTo(layerGroup).bindPopup('Base de Operações (Início)');
      L.marker(latLngs[latLngs.length - 1], { icon: endIcon }).addTo(layerGroup).bindPopup('Última coordenada registrada');

      latLngs.forEach((latLng) => {
        const ll = L.latLng(latLng[0], latLng[1]);
        if (!mainBounds) {
          mainBounds = L.latLngBounds(ll, ll);
        } else {
          mainBounds.extend(ll);
        }
      });
    }

    // Marcadores de corridas particulares
    if (corridasParticulares && corridasParticulares.length > 0) {
      corridasParticulares.forEach((cp) => {
        if (cp.localizacao_inicio?.lat && cp.localizacao_inicio?.lon) {
          const startIconCP = L.divIcon({
            className: 'custom-marker-cp-start',
            html: '<div style="background-color: #6366F1; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [14, 14],
            iconAnchor: [7, 7],
          });
          const startLatLng = L.latLng(cp.localizacao_inicio.lat, cp.localizacao_inicio.lon);
          L.marker(startLatLng, { icon: startIconCP })
            .addTo(layerGroup)
            .bindPopup(`<strong>Corrida Particular (Início)</strong><br/>ID: ${cp.id}<br/>Km Inicial: ${cp.km_inicio} km`);

          if (!mainBounds) {
            mainBounds = L.latLngBounds(startLatLng, startLatLng);
          } else {
            mainBounds.extend(startLatLng);
          }
        }

        if (cp.destino_coordenadas?.lat && cp.destino_coordenadas?.lon) {
          const destIconCP = L.divIcon({
            className: 'custom-marker-cp-dest',
            html: '<div style="background-color: #EC4899; width: 16px; height: 16px; border-radius: 4px; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
          });
          const destLatLng = L.latLng(cp.destino_coordenadas.lat, cp.destino_coordenadas.lon);
          L.marker(destLatLng, { icon: destIconCP })
            .addTo(layerGroup)
            .bindPopup(`<strong>Corrida Particular (Destino)</strong><br/>Endereço: ${cp.destino_endereco || 'Não especificado'}<br/>Distância Estimada: ${cp.google_distancia_km?.toFixed(2) ?? '0.00'} km`);

          if (!mainBounds) {
            mainBounds = L.latLngBounds(destLatLng, destLatLng);
          } else {
            mainBounds.extend(destLatLng);
          }

          if (cp.localizacao_inicio?.lat && cp.localizacao_inicio?.lon) {
            L.polyline([
              [cp.localizacao_inicio.lat, cp.localizacao_inicio.lon],
              [cp.destino_coordenadas.lat, cp.destino_coordenadas.lon]
            ], {
              color: '#8B5CF6',
              weight: 3,
              dashArray: '5, 8',
              opacity: 0.8
            }).addTo(layerGroup);
          }
        }
      });
    }

    if (mainBounds) {
      map.fitBounds(mainBounds, { padding: [30, 30], maxZoom: 16 });
    }
  }, [coordinates, corridasParticulares]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full rounded-lg" />
      
      <div className="absolute bottom-4 right-4 z-[1000] bg-white/95 backdrop-blur-sm px-3.5 py-2.5 rounded-xl shadow-lg border border-slate-200 flex flex-col gap-2 text-xs font-semibold text-slate-700">
        <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Sentido do Deslocamento</div>
        <div className="flex items-center gap-2.5">
          <div className="w-3.5 h-1.5 bg-[#3b82f6] rounded-full" />
          <span>Afastando-se da Base (Outbound)</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-3.5 h-1.5 bg-[#10b981] rounded-full" />
          <span>Aproximando-se da Base (Inbound)</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 bg-[#3b82f6] rounded-full border border-white" />
          <span>Base de Operações</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 bg-[#ef4444] rounded-full border border-white" />
          <span>Último Ponto Registrado</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 bg-[#6366F1] rounded-full border border-white" />
          <span>Partida Corrida Particular</span>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="w-3.5 h-3.5 bg-[#EC4899] rounded-sm border border-white" />
          <span>Destino Corrida Particular</span>
        </div>
      </div>
    </div>
  );
}

// ─── MAPA DE EVENTOS SELECIONADOS ──────────────────────────────────────────
interface SelectedEventsMapProps {
  routes: {
    jornadaId: string;
    motoristaNome: string;
    veiculoId: string;
    segments: [number, number][][];
    stops: { coords: [number, number]; label: string }[];
  }[];
}

function SelectedEventsMap({ routes }: SelectedEventsMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = L.map(mapContainerRef.current).setView([-20.3155, -40.2944], 12);
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    layerGroupRef.current = layerGroup;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    if (routes.length === 0) return;

    let mainBounds: L.LatLngBounds | null = null;
    const colors = ['#3b82f6', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];

    routes.forEach((route, routeIdx) => {
      const color = colors[routeIdx % colors.length];

      // Desenhar cada segmento da rota (separados por paradas)
      route.segments.forEach((seg, segIdx) => {
        if (seg.length < 2) return;
        const poly = L.polyline(seg, {
          color,
          weight: 5,
          opacity: 0.9,
          lineJoin: 'round',
        }).addTo(layerGroup);

        poly.bindPopup(`
          <div class="space-y-1 text-xs">
            <p><strong>Motorista:</strong> ${route.motoristaNome}</p>
            <p><strong>Veículo:</strong> ${route.veiculoId}</p>
            <p class="font-semibold text-blue-600">Trecho ${segIdx + 1}</p>
          </div>
        `);

        if (!mainBounds) {
          mainBounds = poly.getBounds();
        } else {
          mainBounds.extend(poly.getBounds());
        }
      });

      // Marcadores de paradas intermediárias
      route.stops.forEach((stop) => {
        const stopIcon = L.divIcon({
          className: 'custom-stop-marker',
          html: '<div style="background-color: #ef4444; width: 12px; height: 12px; border-radius: 50%; border: 2.5px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>',
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });

        L.marker(stop.coords, { icon: stopIcon })
          .addTo(layerGroup)
          .bindPopup(`<strong>Parada no Trajeto:</strong><br/>${stop.label}`);

        const stopLatLng = L.latLng(stop.coords[0], stop.coords[1]);
        if (!mainBounds) {
          mainBounds = L.latLngBounds(stopLatLng, stopLatLng);
        } else {
          mainBounds.extend(stopLatLng);
        }
      });
    });

    if (mainBounds) {
      map.fitBounds(mainBounds, { padding: [40, 40], maxZoom: 16 });
    }
  }, [routes]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full rounded-lg" />
      <div className="absolute bottom-4 right-4 z-[1000] bg-white/95 backdrop-blur-sm px-3 py-2 rounded-xl shadow-lg border border-slate-200 flex flex-col gap-1.5 text-[11px] font-semibold text-slate-700">
        <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Identificação Visual</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#ef4444] border-2 border-white" />
          <span>Local de Parada (Gera novo trajeto)</span>
        </div>
        <div className="text-[9px] text-slate-400 max-w-[180px] mt-1 font-normal leading-tight">
          Trajetos são divididos automaticamente ao detectar estado PARADO ou hiatos de telemetria superiores a 5 minutos.
        </div>
      </div>
    </div>
  );
}

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const statusBadgeVariant = (status: JourneyStatus) => {
  if (status === 'ENCERRADA') return 'default' as const;
  if (status === 'ABERTA' || status === 'EM_ANDAMENTO') return 'secondary' as const;
  return 'outline' as const;
};

interface TimelineEvent {
  time: string;
  type: 'inicio' | 'fim' | 'pausa' | 'abastecimento';
  title: string;
  description: string;
  icon: React.ReactNode;
  colorClass: string;
}

const getTimelineEvents = (j: Jornada): TimelineEvent[] => {
  const events: TimelineEvent[] = [];

  if ((j as any).corridas_particulares) {
    (j as any).corridas_particulares.forEach((cp: any) => {
      let timeStrIni = '';
      if (cp.horario_inicio) {
        const parts = cp.horario_inicio.split('T');
        timeStrIni = parts.length > 1 ? parts[1].substring(0, 8) : cp.horario_inicio;
      }
      events.push({
        time: timeStrIni || '00:00:00',
        type: 'inicio' as any,
        title: `Corrida Particular Iniciada (ID: ${cp.id})`,
        description: `Destino: ${cp.destino_endereco || 'Não definido'} | Km inicial: ${cp.km_inicio} km`,
        icon: <Compass size={12} weight="fill" />,
        colorClass: 'bg-indigo-500 text-white',
      });

      if (cp.horario_fim) {
        let timeStrFim = '';
        const parts = cp.horario_fim.split('T');
        timeStrFim = parts.length > 1 ? parts[1].substring(0, 8) : cp.horario_fim;
        events.push({
          time: timeStrFim || '00:00:00',
          type: 'fim' as any,
          title: `Corrida Particular Finalizada (ID: ${cp.id})`,
          description: `Valor: R$ ${cp.valor_calculado?.toFixed(2) ?? '0.00'} | Km final: ${cp.km_fim} km (${cp.km_rodados ?? 0} km rodados)`,
          icon: <Flag size={12} weight="fill" />,
          colorClass: 'bg-violet-500 text-white',
        });
      }
    });
  }

  if (j.horario?.inicio) {
    events.push({
      time: j.horario.inicio,
      type: 'inicio',
      title: 'Início da Jornada',
      description: `Odômetro inicial: ${j.km?.inicial?.toLocaleString('pt-BR') ?? '—'} km`,
      icon: <Flag size={12} weight="fill" />,
      colorClass: 'bg-emerald-500 text-white',
    });
  }

  if (j.pausas) {
    j.pausas.forEach((p) => {
      events.push({
        time: p.inicio || '00:00:00',
        type: 'pausa',
        title: `Pausa (${p.tipo})`,
        description: p.fim ? `Fim às ${p.fim}` : 'Em andamento',
        icon: <Coffee size={12} weight="fill" />,
        colorClass: 'bg-amber-500 text-white',
      });
    });
  }

  if (j.abastecimentos) {
    j.abastecimentos.forEach((ab) => {
      const valorTotal = (ab.gnv ?? 0) + (ab.gasolina ?? 0) + (ab.etanol ?? 0);
      const combustivel = ab.gnv ? 'GNV' : ab.gasolina ? 'Gasolina' : ab.etanol ? 'Etanol' : 'Abastecimento';
      
      let timeStr = ab.hora_inicio;
      const timestamp = (ab as any).timestamp;
      if (!timeStr && timestamp && typeof timestamp === 'string') {
        const parts = timestamp.split('T');
        if (parts.length > 1) {
          timeStr = parts[1].substring(0, 8);
        } else {
          timeStr = timestamp;
        }
      }
      
      events.push({
        time: timeStr || '00:00:00',
        type: 'abastecimento',
        title: `Abastecimento (${combustivel})`,
        description: `Total: ${valorTotal.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}${ab.km ? ` | Odômetro: ${ab.km} km` : ''}`,
        icon: <Drop size={12} weight="fill" />,
        colorClass: 'bg-blue-500 text-white',
      });
    });
  }

  if (j.horario?.fim) {
    events.push({
      time: j.horario.fim,
      type: 'fim',
      title: 'Fim da Jornada',
      description: `Odômetro final: ${j.km?.final?.toLocaleString('pt-BR') ?? '—'} km`,
      icon: <Flag size={12} weight="fill" />,
      colorClass: 'bg-rose-500 text-white',
    });
  }

  return events.sort((a, b) => {
    const timeA = a.time || '00:00:00';
    const timeB = b.time || '00:00:00';
    return timeA.localeCompare(timeB);
  });
};

function UnifiedTimeline({ journey }: { journey: Jornada }) {
  const events = getTimelineEvents(journey);

  if (events.length === 0) {
    return <span className="text-muted-foreground text-center block py-8">Nenhum evento registrado nesta jornada.</span>;
  }

  return (
    <div className="relative pl-6 border-l border-slate-200 space-y-6 ml-2 my-2">
      {events.map((e, idx) => (
        <div key={idx} className="relative">
          <div className={`absolute -left-[35px] top-0.5 w-6 h-6 rounded-full flex items-center justify-center shadow-sm ${e.colorClass}`}>
            {e.icon}
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-semibold text-slate-800">{e.title}</span>
              <span className="text-[10px] font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 font-semibold">
                {e.time}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">{e.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function JornadasView() {
  const [activeTab, setActiveTab] = useState<'painel' | 'realtime' | 'importar'>('painel');
  const [search, setSearch] = useState('');
  const [dataFiltro, setDataFiltro] = useState(() => {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  });
  const [selectedJornada, setSelectedJornada] = useState<Jornada | null>(null);
  const [routeCoordinates, setRouteCoordinates] = useState<[number, number][]>([]);
  const [loadingRoute, setLoadingRoute] = useState(false);

  const queryClient = useQueryClient();

  const handleAprovarAuditoria = async () => {
    if (!selectedJornada) return;
    const jId = selectedJornada.id || (selectedJornada as any)._id;
    if (!confirm('Aprovar auditoria da sessão? Isso excluirá fisicamente todas as mídias associadas (fotos de odômetro, avarias e comprovantes de faturamento) e limpará as referências de URL no banco de dados.')) {
      return;
    }
    
    try {
      await api.post(`/jornadas/${jId}/auditoria/aprovar`);
      alert('Auditoria aprovada e mídias removidas com sucesso.');
      setSelectedJornada(null);
      queryClient.invalidateQueries({ queryKey: ['jornadas'] });
    } catch (e) {
      console.error(e);
      alert('Erro ao aprovar auditoria.');
    }
  };

  useEffect(() => {
    if (!selectedJornada) return;
    const status = selectedJornada.status;
    if (status !== 'ABERTA' && status !== 'EM_ANDAMENTO') return;

    const pollRoute = async () => {
      try {
        const jId = selectedJornada.id || (selectedJornada as any)._id;
        const { data } = await api.get(`/gps/motorista/${selectedJornada.motorista_id}/rota-ajustada`, {
          params: { jornada_id: jId }
        });
        if (data && data.coordinates) {
          setRouteCoordinates(data.coordinates);
        }
      } catch (e) {
        console.error('Erro no polling da rota:', e);
      }
    };

    const interval = setInterval(pollRoute, 5000);
    return () => clearInterval(interval);
  }, [selectedJornada]);

  const handleDeleteJornada = async (jId: string) => {
    if (!window.confirm("Tem certeza que deseja apagar esta jornada? Esta ação é irreversível e removerá também todo o histórico de GPS correspondente.")) {
      return;
    }
    try {
      await api.delete(`/jornadas/${jId}`);
      alert("Jornada deletada com sucesso!");
      window.location.reload();
    } catch (e) {
      console.error("Erro ao deletar jornada:", e);
      alert("Erro ao deletar jornada. Apenas administradores ou gestores possuem permissão.");
    }
  };

  const handleDeleteTelemetry = async (jId: string) => {
    if (!window.confirm(`Tem certeza que deseja apagar toda a telemetria (GPS) e a própria jornada para a ID: ${jId}?`)) {
      return;
    }
    try {
      await api.delete(`/gps/jornada/${jId}`);
      alert("Tudo deletado com sucesso para esta jornada!");
      setLiveEvents(prev => prev.filter(ev => ev.jornada_id !== jId));
    } catch (e) {
      console.error("Erro ao deletar telemetria da jornada:", e);
      alert("Erro ao deletar telemetria.");
    }
  };

  // Estados dos eventos em tempo real
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [realtimePage, setRealtimePage] = useState(1);
  const realtimePageSize = 100;
  const [filtroTipoEvento, setFiltroTipoEvento] = useState('');
  const [filtroIntervalo, setFiltroIntervalo] = useState('all');
  const [selectedMotoristaId, setSelectedMotoristaId] = useState<string>('');
  const [motoristas, setMotoristas] = useState<any[]>([]);
  const [datetimeInicio, setDatetimeInicio] = useState(() => {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T00:00`;
  });
  const [datetimeFim, setDatetimeFim] = useState(() => {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T23:59`;
  });

  const dataFiltroRealtime = datetimeInicio ? datetimeInicio.split('T')[0] : '';
  const horaInicio = datetimeInicio && datetimeInicio.includes('T') ? datetimeInicio.split('T')[1] : '';
  const horaFim = datetimeFim && datetimeFim.includes('T') ? datetimeFim.split('T')[1] : '';

  // Carrega a lista de motoristas para o Combobox
  useEffect(() => {
    const loadMotoristas = async () => {
      try {
        const { data } = await api.get('/users', { params: { role: 'MOTORISTA' } });
        setMotoristas(data);
      } catch (e) {
        console.error('Erro ao carregar motoristas:', e);
      }
    };
    loadMotoristas();
  }, []);

  // Seleção múltipla de eventos e cache de GPS
  const [selectedEvents, setSelectedEvents] = useState<any[]>([]);
  const [gpsCache, setGpsCache] = useState<Record<string, any[]>>({});

  // Paginação e controle de carregamento sob demanda
  const [mostrarTodas, setMostrarTodas] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const shouldFetchJornadas = activeTab === 'painel' && (!!dataFiltro || mostrarTodas);

  const { data: jornadas = [], isLoading } = useJornadas({
    motorista_id: search || undefined,
    data: dataFiltro || undefined,
    page: shouldFetchJornadas ? currentPage : 1,
    size: shouldFetchJornadas ? pageSize : 0,
    enabled: shouldFetchJornadas,
  });

  // Limpa estados ao alternar de aba
  useEffect(() => {
    setSelectedJornada(null);
    setSelectedEvents([]);
    setRouteCoordinates([]);
    setLiveEvents([]);
    setSelectedMotoristaId('');
    setFiltroTipoEvento('');
    setFiltroIntervalo('all');
    setDatetimeInicio('');
    setDatetimeFim('');
  }, [activeTab]);

  // Função utilitária para conversão de datas livre de fuso horário
  const getSafeTime = (ts: any): number => {
    if (!ts) return 0;
    if (typeof ts === 'string') {
      let cleaned = ts.trim().replace(' ', 'T');
      if (!cleaned.endsWith('Z') && !cleaned.includes('+') && !cleaned.includes('-')) {
        cleaned += 'Z';
      }
      const d = new Date(cleaned);
      if (!isNaN(d.getTime())) return d.getTime();
    }
    return new Date(ts).getTime();
  };

  const getSafeDate = (ts: any): Date => {
    if (!ts) return new Date();
    if (typeof ts === 'string') {
      let cleaned = ts.trim().replace(' ', 'T');
      if (!cleaned.endsWith('Z') && !cleaned.includes('+') && !cleaned.includes('-')) {
        cleaned += 'Z';
      }
      const d = new Date(cleaned);
      if (!isNaN(d.getTime())) return d;
    }
    return new Date(ts);
  };

  const formatDateTime = (ts: any): string => {
    const d = getSafeDate(ts);
    if (isNaN(d.getTime())) return String(ts);
    try {
      return d.toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    } catch (e) {
      return d.toLocaleString('pt-BR');
    }
  };

  const formatTimeOnly = (ts: any): string => {
    const d = getSafeDate(ts);
    if (isNaN(d.getTime())) return String(ts);
    try {
      return d.toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    } catch (e) {
      return d.toLocaleTimeString('pt-BR');
    }
  };

  // Função para carregar o GPS bruto de uma jornada
  const fetchGpsForJornada = async (motoristaId: string, jornadaId: string) => {
    if (gpsCache[jornadaId]) return gpsCache[jornadaId];
    try {
      const { data } = await api.get(`/gps/motorista/${motoristaId}`, {
        params: { jornada_id: jornadaId, limite: 10000 }
      });
      // Converter para ordem cronológica ascendente
      const chronoData = [...data].reverse();
      setGpsCache(prev => ({ ...prev, [jornadaId]: chronoData }));
      return chronoData;
    } catch (e) {
      console.error('Erro ao buscar GPS bruto:', e);
      return [];
    }
  };

  // Alternar seleção de um evento individual
  const handleToggleEvent = async (ev: any) => {
    const isSelected = selectedEvents.some(
      x => x.timestamp === ev.timestamp && x.jornada_id === ev.jornada_id
    );
    let nextSelected;
    if (isSelected) {
      nextSelected = selectedEvents.filter(
        x => !(x.timestamp === ev.timestamp && x.jornada_id === ev.jornada_id)
      );
    } else {
      nextSelected = [...selectedEvents, ev];
      await fetchGpsForJornada(ev.motorista_id, ev.jornada_id);
    }
    setSelectedEvents(nextSelected);
  };



  // Processa as coordenadas dos eventos selecionados e divide nas paradas
  const selectedRoutes = useMemo(() => {
    const groups: Record<string, any[]> = {};
    selectedEvents.forEach((ev) => {
      if (!groups[ev.jornada_id]) groups[ev.jornada_id] = [];
      groups[ev.jornada_id].push(ev);
    });

    const routesList: {
      jornadaId: string;
      motoristaNome: string;
      veiculoId: string;
      segments: [number, number][][];
      stops: { coords: [number, number]; label: string }[];
    }[] = [];

    Object.entries(groups).forEach(([jornadaId, evs]) => {
      const points = gpsCache[jornadaId];
      if (!points || points.length === 0) return;

      // Ordenar eventos selecionados cronologicamente
      const sortedEvs = [...evs].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
      const tStart = getSafeTime(sortedEvs[0].timestamp);
      const tEnd = getSafeTime(sortedEvs[sortedEvs.length - 1].timestamp);

      // Filtrar pontos do GPS no intervalo dos eventos
      const inRangePoints = points.filter((pt) => {
        const ptTime = getSafeTime(pt.timestamp);
        return ptTime >= tStart && ptTime <= tEnd;
      });

      if (inRangePoints.length === 0) return;

      const segments: [number, number][][] = [];
      const stops: { coords: [number, number]; label: string }[] = [];
      let currentSeg: [number, number][] = [];

      for (let i = 0; i < inRangePoints.length; i++) {
        const pt = inRangePoints[i];
        const coords: [number, number] = [
          pt.localizacao.coordinates[1],
          pt.localizacao.coordinates[0],
        ];

        // Se o status for PARADO, encerra o trajeto atual e cria ponto de parada
        if (pt.status === 'PARADO') {
          if (currentSeg.length > 0) {
            segments.push(currentSeg);
            currentSeg = [];
          }
          stops.push({
            coords,
            label: `Parada às ${formatTimeOnly(pt.timestamp)}`,
          });
        } else {
          // Verificar hifens temporais superiores a 5 minutos
          if (i > 0) {
            const prevPt = inRangePoints[i - 1];
            const gapSec = (getSafeTime(pt.timestamp) - getSafeTime(prevPt.timestamp)) / 1000;
            if (gapSec > 300) {
              if (currentSeg.length > 0) {
                segments.push(currentSeg);
                currentSeg = [];
              }
              stops.push({
                coords,
                label: `Intervalo operacional de ${Math.round(gapSec / 60)} min`,
              });
            }
          }
          currentSeg.push(coords);
        }
      }

      if (currentSeg.length > 0) {
        segments.push(currentSeg);
      }

      routesList.push({
        jornadaId,
        motoristaNome: sortedEvs[0].motorista_nome,
        veiculoId: sortedEvs[0].veiculo_id,
        segments,
        stops,
      });
    });

    return routesList;
  }, [selectedEvents, gpsCache]);

  // Polling simulando triggers do MongoDB (Change Stream)
  useEffect(() => {
    if (activeTab !== 'realtime') return;
    if (!selectedMotoristaId) {
      setLiveEvents([]);
      return;
    }

    const fetchLiveEvents = async () => {
      try {
        const dataInicioStr = datetimeInicio ? datetimeInicio.split('T')[0] : undefined;
        const dataFimStr = datetimeFim ? datetimeFim.split('T')[0] : undefined;
        const { data } = await api.get('/jornadas/eventos', {
          params: { 
            motorista_id: selectedMotoristaId,
            data_inicio: dataInicioStr,
            data_fim: dataFimStr
          }
        });
        setLiveEvents(data);
      } catch (e) {
        console.error('Erro ao buscar eventos em tempo real:', e);
      }
    };

    fetchLiveEvents();
    const interval = setInterval(fetchLiveEvents, 3000);
    return () => clearInterval(interval);
  }, [activeTab, selectedMotoristaId, datetimeInicio, datetimeFim]);

  useEffect(() => {
    setRealtimePage(1);
  }, [selectedMotoristaId, datetimeInicio, datetimeFim, filtroTipoEvento, filtroIntervalo]);

  // Prefetch automático do GPS completo ao receber a lista de eventos
  useEffect(() => {
    if (liveEvents.length === 0) return;
    const uniqueJornadas = Array.from(new Set(liveEvents.map(ev => ev.jornada_id).filter(Boolean)));
    uniqueJornadas.forEach((jId) => {
      const ev = liveEvents.find(e => e.jornada_id === jId);
      if (ev) {
        fetchGpsForJornada(ev.motorista_id, jId);
      }
    });
  }, [liveEvents]);

  const handleOpenJornada = async (j: Jornada) => {
    setSelectedJornada(j);
    setLoadingRoute(true);
    setRouteCoordinates([]);
    try {
      const jId = j.id || (j as any)._id;
      const { data } = await api.get(`/gps/motorista/${j.motorista_id}/rota-ajustada`, {
        params: { jornada_id: jId }
      });
      if (data && data.coordinates) {
        setRouteCoordinates(data.coordinates);
      }
    } catch (e) {
      console.error('Erro ao buscar rota ajustada:', e);
    } finally {
      setLoadingRoute(false);
    }
  };

  const handleOpenJornadaFromEvent = async (jornadaId: string) => {
    setLoadingRoute(true);
    setActiveTab('painel');
    try {
      const { data: j } = await api.get(`/jornadas/${jornadaId}`);
      setSelectedJornada(j);
      const { data: routeData } = await api.get(`/gps/motorista/${j.motorista_id}/rota-ajustada`, {
        params: { jornada_id: j.id || (j as any)._id }
      });
      if (routeData && routeData.coordinates) {
        setRouteCoordinates(routeData.coordinates);
      }
    } catch (e) {
      console.error('Erro ao abrir jornada do evento:', e);
    } finally {
      setLoadingRoute(false);
    }
  };

  const kmByDriver = jornadas.reduce<{ name: string; km: number }[]>((acc, j) => {
    const nome = (j.motorista_nome ?? j.motorista_id).split(' ')[0];
    const existing = acc.find((d) => d.name === nome);
    if (existing) {
      existing.km += j.km?.rodados ?? 0;
    } else {
      acc.push({ name: nome, km: j.km?.rodados ?? 0 });
    }
    return acc;
  }, []).sort((a, b) => b.km - a.km);

  // Filtragem
  const filteredEvents = (() => {
    let gpsIndex = 0;
    return liveEvents.filter((ev) => {
      const matchesTipo = filtroTipoEvento ? ev.tipo === filtroTipoEvento : true;
      if (!matchesTipo) return false;

      // Filtro por intervalo de horário (HH:MM)
      if (horaInicio || horaFim) {
        const evDate = getSafeDate(ev.timestamp);
        let evTimeStr = '';
        try {
          evTimeStr = new Intl.DateTimeFormat('pt-BR', {
            timeZone: 'America/Sao_Paulo',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
          }).format(evDate);
        } catch (e) {
          const evHours = evDate.getHours();
          const evMinutes = evDate.getMinutes();
          evTimeStr = `${String(evHours).padStart(2, '0')}:${String(evMinutes).padStart(2, '0')}`;
        }
        
        if (horaInicio && evTimeStr < horaInicio) return false;
        if (horaFim && evTimeStr > horaFim) return false;
      }

      if (ev.tipo === 'TELEMETRIA_GPS') {
        gpsIndex++;
        if (filtroIntervalo === 'events_only') {
          return false;
        }
        if (filtroIntervalo === '1min' && gpsIndex % 4 !== 0) {
          return false;
        }
        if (filtroIntervalo === '5min' && gpsIndex % 20 !== 0) {
          return false;
        }
        if (filtroIntervalo === '10min' && gpsIndex % 40 !== 0) {
          return false;
        }
      }
      return true;
    });
  })();

  const paginatedEvents = filteredEvents.slice((realtimePage - 1) * realtimePageSize, realtimePage * realtimePageSize);

  // Estados do Seletor de Faixa por Arrasto (Timeline Range Drag Selector)
  const isTrackDraggingRef = useRef(false);
  const trackStartIdxRef = useRef<number | null>(null);
  const [trackHoverIdx, setTrackHoverIdx] = useState<number | null>(null);
  const dragSelectModeRef = useRef<boolean>(true);

  // Reseta ao mudar filtros
  useEffect(() => {
    trackStartIdxRef.current = null;
    isTrackDraggingRef.current = false;
    setTrackHoverIdx(null);
  }, [activeTab, filtroTipoEvento, filtroIntervalo, selectedMotoristaId, horaInicio, horaFim]);

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (isTrackDraggingRef.current && trackStartIdxRef.current !== null && trackHoverIdx !== null) {
        if (dragSelectModeRef.current) {
          const start = Math.min(trackStartIdxRef.current, trackHoverIdx);
          const end = Math.max(trackStartIdxRef.current, trackHoverIdx);
          const eventsInRange = filteredEvents.slice(start, end + 1);
          
          eventsInRange.forEach((ev) => {
            fetchGpsForJornada(ev.motorista_id, ev.jornada_id);
          });
          
          // Permite apenas seleção contínua: substitui a seleção anterior completamente
          setSelectedEvents(eventsInRange);
        } else {
          // Desfazer seleção: limpa a seleção completamente
          setSelectedEvents([]);
        }
      }
      
      isTrackDraggingRef.current = false;
      trackStartIdxRef.current = null;
      setTrackHoverIdx(null);
    };
    
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, [trackHoverIdx, filteredEvents]);

  const handleTrackMouseDown = (e: React.MouseEvent, idx: number) => {
    e.preventDefault();
    isTrackDraggingRef.current = true;
    trackStartIdxRef.current = idx;
    
    const ev = filteredEvents[idx];
    const isAlreadySelected = selectedEvents.some(
      x => x.timestamp === ev.timestamp && x.jornada_id === ev.jornada_id
    );
    dragSelectModeRef.current = !isAlreadySelected;
    setTrackHoverIdx(idx);
  };

  const handleTrackMouseEnter = (idx: number) => {
    if (!isTrackDraggingRef.current) return;
    setTrackHoverIdx(idx);
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => { setActiveTab('painel'); setSelectedJornada(null); }}
          className={`pb-3 font-semibold text-sm transition-all relative ${
            activeTab === 'painel' 
              ? 'text-primary border-b-2 border-blue-600' 
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <MapTrifold size={18} />
            <span>Painel e Trajetos</span>
          </div>
        </button>

        <button
          onClick={() => { setActiveTab('realtime'); setSelectedJornada(null); }}
          className={`pb-3 font-semibold text-sm transition-all relative ${
            activeTab === 'realtime' 
              ? 'text-primary border-b-2 border-blue-600' 
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <ListBullets size={18} />
            <div className="flex items-center gap-1.5">
              <span>Eventos em Tempo Real</span>
              <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
            </div>
          </div>
        </button>

        <button
          onClick={() => { setActiveTab('importar'); setSelectedJornada(null); }}
          className={`pb-3 font-semibold text-sm transition-all relative ${
            activeTab === 'importar' 
              ? 'text-primary border-b-2 border-blue-600' 
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <div className="flex items-center gap-2">
            <UploadSimple size={18} />
            <span>Importação Uber/99</span>
          </div>
        </button>
      </div>

      {activeTab === 'painel' && (
        <>
          {selectedJornada ? (
            <div className="space-y-6 animate-fade-in">
              <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                <div className="flex items-center gap-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedJornada(null)}
                    className="flex items-center gap-2 px-3 py-1.5 h-auto text-slate-700 border-slate-200 shadow-sm hover:bg-slate-50 transition-colors"
                  >
                    <ArrowLeft size={16} />
                    Voltar
                  </Button>
                  <div>
                    <h2 className="text-2xl font-bold text-slate-800">Visualizar Jornada</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Deslocamento real e eventos ocorridos em {new Date(selectedJornada.data).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={statusBadgeVariant(selectedJornada.status)} className="px-3 py-1 text-sm font-semibold uppercase tracking-wider">
                    {selectedJornada.status}
                  </Badge>
                  <Badge 
                    variant={selectedJornada.auditoria_status === 'APROVADA' ? 'outline' : 'secondary'} 
                    className={`px-3 py-1 text-sm font-semibold uppercase tracking-wider ${
                      selectedJornada.auditoria_status === 'APROVADA' 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    Auditoria: {selectedJornada.auditoria_status || 'PENDENTE'}
                  </Badge>

                  {selectedJornada.status === 'ENCERRADA' && selectedJornada.auditoria_status !== 'APROVADA' && (
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={handleAprovarAuditoria}
                      className="border-emerald-500 text-emerald-500 hover:bg-emerald-500 hover:text-white font-semibold"
                    >
                      <ShieldCheck size={18} className="mr-1.5" />
                      Aprovar Auditoria
                    </Button>
                  )}
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4 flex items-center gap-4 bg-card shadow-sm border border-slate-100 rounded-xl">
                  <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                    <User size={24} weight="duotone" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Motorista</p>
                    <h4 className="text-sm font-semibold text-slate-800 mt-0.5">
                      {selectedJornada.motorista_nome ?? selectedJornada.motorista_id}
                    </h4>
                  </div>
                </Card>

                <Card className="p-4 flex items-center gap-4 bg-card shadow-sm border border-slate-100 rounded-xl">
                  <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl">
                    <Car size={24} weight="duotone" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Veículo / Placa</p>
                    <h4 className="text-sm font-semibold text-slate-800 mt-0.5">{selectedJornada.veiculo_id}</h4>
                  </div>
                </Card>

                <Card className="p-4 flex items-center gap-4 bg-card shadow-sm border border-slate-100 rounded-xl">
                  <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl">
                    <Compass size={24} weight="duotone" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Odômetro Inicial / Final</p>
                    <h4 className="text-sm font-semibold text-slate-800 mt-0.5">
                      {selectedJornada.km?.inicial?.toLocaleString('pt-BR') ?? '—'} / {selectedJornada.km?.final?.toLocaleString('pt-BR') ?? '—'}
                    </h4>
                  </div>
                </Card>

                <Card className="p-4 flex items-center gap-4 bg-card shadow-sm border border-slate-100 rounded-xl">
                  <div className="p-3 bg-rose-50 text-rose-600 rounded-xl">
                    <Clock size={24} weight="duotone" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Km Rodados</p>
                    <h4 className="text-sm font-bold text-blue-600 mt-0.5">
                      {selectedJornada.km?.rodados?.toLocaleString('pt-BR') ?? 0} km
                    </h4>
                  </div>
                </Card>
              </div>

              {/* Main Content Layout */}
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                <div className="xl:col-span-2 space-y-3">
                  <div className="flex items-center gap-2">
                    <MapTrifold size={20} className="text-slate-600" />
                    <h3 className="text-lg font-semibold text-slate-700">Deslocamento Contínuo e Direção da Rota</h3>
                  </div>
                  <Card className="overflow-hidden border border-slate-100 shadow-md rounded-2xl h-[550px] relative">
                    {loadingRoute ? (
                      <div className="w-full h-full flex items-center justify-center bg-slate-50">
                        <span className="text-sm text-slate-500 animate-pulse">Carregando telemetria...</span>
                      </div>
                    ) : (routeCoordinates.length > 0 || (selectedJornada.corridas_particulares && selectedJornada.corridas_particulares.length > 0)) ? (
                      <div className="w-full h-full relative">
                        <JourneyMap 
                          coordinates={routeCoordinates} 
                          corridasParticulares={selectedJornada.corridas_particulares}
                        />
                      </div>
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50 text-center p-6">
                        <span className="text-sm text-slate-500 font-semibold">Sem dados de telemetria</span>
                        <span className="text-xs text-slate-400 mt-1.5 max-w-sm">
                          Não foram encontradas coordenadas geográficas para esta jornada.
                        </span>
                      </div>
                    )}
                  </Card>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Clock size={20} className="text-slate-600" />
                    <h3 className="text-lg font-semibold text-slate-700">Linha do Tempo</h3>
                  </div>
                  <Card className="p-6 border border-slate-100 shadow-md rounded-2xl h-[550px] overflow-y-auto bg-card">
                    <UnifiedTimeline journey={selectedJornada} />
                  </Card>
                </div>
              </div>

              {/* Fotografias e Comprovantes */}
              {(selectedJornada.fotos?.km_inicial_url || 
                selectedJornada.fotos?.km_final_url || 
                selectedJornada.vistoria?.foto_avarias_url ||
                selectedJornada.faturamento?.comprovante_uber_url ||
                selectedJornada.faturamento?.comprovante_99_url ||
                selectedJornada.faturamento?.comprovante_outros_url) && (
                <div className="mt-6 border-t border-slate-100 pt-6">
                  <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                    <Camera size={18} className="text-slate-600" />
                    Fotografias e Comprovantes da Jornada
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    {selectedJornada.fotos?.km_inicial_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Odômetro Inicial</span>
                        <a 
                          href={selectedJornada.fotos.km_inicial_url.startsWith('http') ? selectedJornada.fotos.km_inicial_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.fotos.km_inicial_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity"
                        >
                          <img 
                            src={selectedJornada.fotos.km_inicial_url.startsWith('http') ? selectedJornada.fotos.km_inicial_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.fotos.km_inicial_url}`}
                            alt="Odômetro Inicial" 
                            className="w-full h-full object-cover" 
                          />
                        </a>
                      </Card>
                    )}
                    {selectedJornada.fotos?.km_final_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Odômetro Final</span>
                        <a 
                          href={selectedJornada.fotos.km_final_url.startsWith('http') ? selectedJornada.fotos.km_final_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.fotos.km_final_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity"
                        >
                          <img 
                            src={selectedJornada.fotos.km_final_url.startsWith('http') ? selectedJornada.fotos.km_final_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.fotos.km_final_url}`}
                            alt="Odômetro Final" 
                            className="w-full h-full object-cover" 
                          />
                        </a>
                      </Card>
                    )}
                    {selectedJornada.vistoria?.foto_avarias_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Avarias Vistoria</span>
                        <a 
                          href={selectedJornada.vistoria.foto_avarias_url.startsWith('http') ? selectedJornada.vistoria.foto_avarias_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.vistoria.foto_avarias_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity"
                        >
                          <img 
                            src={selectedJornada.vistoria.foto_avarias_url.startsWith('http') ? selectedJornada.vistoria.foto_avarias_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.vistoria.foto_avarias_url}`}
                            alt="Foto Avarias" 
                            className="w-full h-full object-cover" 
                          />
                        </a>
                      </Card>
                    )}
                    {selectedJornada.faturamento?.comprovante_uber_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Comprovante Uber</span>
                        <a 
                          href={selectedJornada.faturamento.comprovante_uber_url.startsWith('http') ? selectedJornada.faturamento.comprovante_uber_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_uber_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity flex items-center justify-center bg-slate-50"
                        >
                          {selectedJornada.faturamento.comprovante_uber_url.endsWith('.pdf') ? (
                            <span className="text-xs font-semibold text-red-500">Visualizar PDF</span>
                          ) : (
                            <img 
                              src={selectedJornada.faturamento.comprovante_uber_url.startsWith('http') ? selectedJornada.faturamento.comprovante_uber_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_uber_url}`}
                              alt="Comprovante Uber" 
                              className="w-full h-full object-cover" 
                            />
                          )}
                        </a>
                      </Card>
                    )}
                    {selectedJornada.faturamento?.comprovante_99_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Comprovante 99</span>
                        <a 
                          href={selectedJornada.faturamento.comprovante_99_url.startsWith('http') ? selectedJornada.faturamento.comprovante_99_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_99_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity flex items-center justify-center bg-slate-50"
                        >
                          {selectedJornada.faturamento.comprovante_99_url.endsWith('.pdf') ? (
                            <span className="text-xs font-semibold text-red-500">Visualizar PDF</span>
                          ) : (
                            <img 
                              src={selectedJornada.faturamento.comprovante_99_url.startsWith('http') ? selectedJornada.faturamento.comprovante_99_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_99_url}`}
                              alt="Comprovante 99" 
                              className="w-full h-full object-cover" 
                            />
                          )}
                        </a>
                      </Card>
                    )}
                    {selectedJornada.faturamento?.comprovante_outros_url && (
                      <Card className="p-3 border border-slate-100 shadow-sm rounded-xl flex flex-col items-center gap-2">
                        <span className="text-[10px] font-bold text-muted-foreground uppercase text-center">Comprovante Outros</span>
                        <a 
                          href={selectedJornada.faturamento.comprovante_outros_url.startsWith('http') ? selectedJornada.faturamento.comprovante_outros_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_outros_url}`}
                          target="_blank" 
                          rel="noreferrer"
                          className="w-full h-32 rounded-lg overflow-hidden border border-slate-100 block hover:opacity-85 transition-opacity flex items-center justify-center bg-slate-50"
                        >
                          {selectedJornada.faturamento.comprovante_outros_url.endsWith('.pdf') ? (
                            <span className="text-xs font-semibold text-red-500">Visualizar PDF</span>
                          ) : (
                            <img 
                              src={selectedJornada.faturamento.comprovante_outros_url.startsWith('http') ? selectedJornada.faturamento.comprovante_outros_url : `${api.defaults.baseURL?.replace('/api', '')}${selectedJornada.faturamento.comprovante_outros_url}`}
                              alt="Comprovante Outros" 
                              className="w-full h-full object-cover" 
                            />
                          )}
                        </a>
                      </Card>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              <div className="flex gap-4 flex-wrap items-center">
                <Input
                  placeholder="Filtrar por nome do motorista..."
                  className="max-w-xs text-xs"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setCurrentPage(1);
                  }}
                />
                <Input
                  type="date"
                  className="max-w-xs text-xs"
                  value={dataFiltro}
                  onChange={(e) => {
                    setDataFiltro(e.target.value);
                    setCurrentPage(1);
                    if (e.target.value) {
                      setMostrarTodas(false);
                    }
                  }}
                />
                {dataFiltro && (
                  <Button variant="outline" size="sm" className="text-xs" onClick={() => {
                    setDataFiltro('');
                    setCurrentPage(1);
                  }}>
                    Limpar filtro
                  </Button>
                )}

                <Button 
                  variant={mostrarTodas ? "default" : "outline"}
                  size="sm"
                  className="text-xs"
                  onClick={() => {
                    const next = !mostrarTodas;
                    setMostrarTodas(next);
                    setCurrentPage(1);
                    if (next) {
                      setDataFiltro('');
                    }
                  }}
                >
                  {mostrarTodas ? "Ocultar Jornadas" : "Mostrar Todas as Datas"}
                </Button>
              </div>

              {!dataFiltro && !mostrarTodas ? (
                <div className="flex flex-col items-center justify-center py-16 bg-slate-50 border border-dashed border-slate-200 rounded-2xl text-center px-4">
                  <div className="p-4 bg-blue-50 text-blue-600 rounded-full mb-4">
                    <Calendar size={32} weight="duotone" />
                  </div>
                  <h4 className="text-base font-semibold text-slate-800">Painel de Jornadas</h4>
                  <p className="text-xs text-slate-500 mt-1.5 max-w-md">
                    Selecione uma data no filtro para ver as jornadas daquele dia, ou clique em <strong>"Mostrar Todas as Datas"</strong> para listar todos os registros cadastrados de forma paginada.
                  </p>
                </div>
              ) : isLoading ? (
                <Skeleton className="h-80 w-full rounded-xl" />
              ) : (
                <>
                  {kmByDriver.length > 0 && (
                    <Card className="p-6">
                      <h3 className="text-lg font-semibold mb-4">Km Rodados por Motorista</h3>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={kmByDriver} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis type="number" tick={{ fontSize: 12 }} />
                          <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={80} />
                          <Tooltip />
                          <Bar dataKey="km" fill="#3b82f6" name="Km Rodados" />
                        </BarChart>
                      </ResponsiveContainer>
                    </Card>
                  )}

                  <Card className="p-6">
                    <div className="flex flex-wrap justify-between items-center gap-4 mb-4 pb-2 border-b border-slate-100">
                      <div>
                        <h3 className="text-lg font-semibold text-slate-850">Jornadas Cadastradas</h3>
                        <p className="text-xs text-slate-400 mt-0.5">
                          {dataFiltro 
                            ? `Jornadas do dia ${new Date(dataFiltro + 'T00:00:00').toLocaleDateString('pt-BR')}`
                            : "Todas as jornadas cadastradas no sistema"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs"
                          disabled={currentPage === 1 || isLoading}
                          onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        >
                          Anterior
                        </Button>
                        <span className="text-xs text-slate-600 font-mono font-medium px-2">
                          Pág. {currentPage}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs"
                          disabled={jornadas.length < pageSize || isLoading}
                          onClick={() => setCurrentPage(prev => prev + 1)}
                        >
                          Próxima
                        </Button>
                      </div>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Data</TableHead>
                          <TableHead>Motorista</TableHead>
                          <TableHead>Veículo</TableHead>
                          <TableHead>Início</TableHead>
                          <TableHead>Fim</TableHead>
                          <TableHead>Km Rodados</TableHead>
                          <TableHead>Faturamento</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Ações</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {jornadas.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                              Nenhuma jornada encontrada.
                            </TableCell>
                          </TableRow>
                        ) : (
                          jornadas.map((j) => (
                            <TableRow key={j.id || (j as any)._id}>
                              <TableCell>{new Date(j.data + 'T00:00:00').toLocaleDateString('pt-BR')}</TableCell>
                              <TableCell className="font-medium">
                                {j.motorista_nome ?? j.motorista_id}
                              </TableCell>
                              <TableCell>{j.veiculo_id}</TableCell>
                              <TableCell>{j.horario?.inicio ?? '—'}</TableCell>
                              <TableCell>{j.horario?.fim ?? '—'}</TableCell>
                              <TableCell>{j.km?.rodados ?? 0} km</TableCell>
                              <TableCell>{formatCurrency(j.faturamento?.total_dia ?? 0)}</TableCell>
                              <TableCell>
                                <Badge variant={statusBadgeVariant(j.status)}>{j.status}</Badge>
                              </TableCell>
                              <TableCell>
                                <div className="flex gap-2">
                                  <Button size="sm" variant="ghost" onClick={() => handleOpenJornada(j)}>
                                    <Eye size={16} />
                                  </Button>
                                  <Button size="sm" variant="ghost" onClick={() => handleDeleteJornada(j.id || (j as any)._id)} className="text-red-500 hover:text-red-700 hover:bg-red-50">
                                    <Trash size={16} />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </Card>
                </>
              )}
            </div>
          )}
        </>
      )}

      {activeTab === 'realtime' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-xl font-bold text-slate-800">Eventos em Tempo Real</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Selecione múltiplos eventos para visualizar e segmentar a rota percorrida no mapa
              </p>
            </div>
            <div className="flex items-center gap-3">
              {selectedEvents.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedEvents([])}
                  className="flex items-center gap-2 border-red-200 text-red-600 hover:bg-red-50 text-xs px-3 py-1.5 h-auto"
                >
                  <Trash size={14} />
                  Limpar Seleção ({selectedEvents.length})
                </Button>
              )}
              <div className="flex items-center gap-2 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-semibold animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Conexão Ativa
              </div>
            </div>
          </div>

          <div className="flex gap-4 items-center flex-wrap">
            <select
              value={selectedMotoristaId}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedMotoristaId(val);
                setSelectedEvents([]); // Limpa a seleção ao trocar de motorista
                if (val && !datetimeInicio) {
                  const now = new Date();
                  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                  const tomorrow = new Date(now.getTime() + 24 * 60 * 60 * 1000);
                  const formatDate = (d: Date) => {
                    const year = d.getFullYear();
                    const month = String(d.getMonth() + 1).padStart(2, '0');
                    const day = String(d.getDate()).padStart(2, '0');
                    return `${year}-${month}-${day}`;
                  };
                  setDatetimeInicio(`${formatDate(yesterday)}T00:00`);
                  setDatetimeFim(`${formatDate(tomorrow)}T23:59`);
                }
              }}
              className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg p-2 focus:outline-none min-w-[200px] shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Selecione o Motorista...</option>
              {motoristas.map((m) => (
                <option key={m.id || m._id} value={m.id || m._id}>
                  {m.nome} ({m.email})
                </option>
              ))}
            </select>

            {selectedMotoristaId && (
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1 shadow-sm">
                <span className="text-xs font-medium text-slate-400">De:</span>
                <input
                  type="datetime-local"
                  value={datetimeInicio}
                  onChange={(e) => {
                    const val = e.target.value;
                    setDatetimeInicio(val);
                    setSelectedEvents([]);
                    if (val) {
                      const datePart = val.split('T')[0];
                      if (!datetimeFim || !datetimeFim.startsWith(datePart)) {
                        setDatetimeFim(`${datePart}T23:59`);
                      }
                    }
                  }}
                  className="text-xs font-semibold text-slate-700 focus:outline-none bg-transparent"
                />
                <span className="text-xs font-medium text-slate-400">Até:</span>
                <input
                  type="datetime-local"
                  value={datetimeFim}
                  onChange={(e) => {
                    setDatetimeFim(e.target.value);
                    setSelectedEvents([]);
                  }}
                  className="text-xs font-semibold text-slate-700 focus:outline-none bg-transparent"
                />
                {(datetimeInicio || datetimeFim) && (
                  <button
                    onClick={() => {
                      setDatetimeInicio('');
                      setDatetimeFim('');
                      setSelectedEvents([]);
                    }}
                    className="text-xs font-semibold text-red-500 hover:text-red-750 ml-1 transition-colors"
                    title="Limpar filtro de data/hora"
                  >
                    Limpar
                  </button>
                )}
              </div>
            )}

            {selectedMotoristaId && dataFiltroRealtime && (
              <select
                value={filtroTipoEvento}
                onChange={(e) => {
                  setFiltroTipoEvento(e.target.value);
                  setSelectedEvents([]);
                }}
                className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg p-2 focus:outline-none shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Todos os tipos de evento</option>
                <option value="INICIO_JORNADA">Início de Jornada</option>
                <option value="ABASTECIMENTO">Abastecimento</option>
                <option value="INICIO_INTERVALO">Início de Intervalo</option>
                <option value="FIM_INTERVALO">Fim de Intervalo</option>
                <option value="FIM_JORNADA">Fim de Jornada</option>
                <option value="TELEMETRIA_GPS">Telemetria GPS (15s)</option>
              </select>
            )}

            {selectedMotoristaId && dataFiltroRealtime && (
              <select
                value={filtroIntervalo}
                onChange={(e) => {
                  setFiltroIntervalo(e.target.value);
                  setSelectedEvents([]);
                }}
                className="text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg p-2 focus:outline-none shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">Amostragem: Completa (15s)</option>
                <option value="1min">Amostragem: 1 minuto</option>
                <option value="5min">Amostragem: 5 minutos</option>
                <option value="10min">Amostragem: 10 minutos</option>
                <option value="events_only">Amostragem: Ocultar Telemetria</option>
              </select>
            )}
          </div>

          {!selectedMotoristaId ? (
            <Card className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-4 border-dashed border-2 border-slate-200 max-w-2xl mx-auto mt-6">
              <div className="p-4 bg-slate-50 rounded-full">
                <User size={36} className="text-slate-400" />
              </div>
              <div className="space-y-1">
                <div className="font-semibold text-slate-700 text-sm">Nenhum Motorista Selecionado</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  Selecione um motorista no combobox acima para carregar o histórico de eventos e telemetria GPS.
                </p>
              </div>
            </Card>
          ) : !dataFiltroRealtime ? (
            <Card className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-4 border-dashed border-2 border-slate-200 max-w-2xl mx-auto mt-6">
              <div className="p-4 bg-slate-50 rounded-full">
                <Calendar size={36} className="text-slate-400" />
              </div>
              <div className="space-y-1">
                <div className="font-semibold text-slate-700 text-sm">Nenhuma Data Selecionada</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  Selecione a data no filtro acima para visualizar a telemetria e eventos ocorridos nesse dia.
                </p>
              </div>
            </Card>
          ) : (
            /* Layout Split-Screen dinâmico ao selecionar eventos */
            <div className={`grid grid-cols-1 gap-6 ${selectedEvents.length > 0 ? 'lg:grid-cols-5' : ''}`}>
              {/* Tabela de Eventos */}
              <Card className={`p-6 ${selectedEvents.length > 0 ? 'lg:col-span-3' : 'w-full'}`}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[50px] text-center">Faixa</TableHead>
                      <TableHead>Horário (São Paulo)</TableHead>
                      <TableHead>Motorista</TableHead>
                      <TableHead>Veículo</TableHead>
                      <TableHead>Evento</TableHead>
                      <TableHead>KM</TableHead>
                      <TableHead className="w-[80px] text-right">Ação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredEvents.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                          Nenhum evento registrado recentemente para este motorista.
                        </TableCell>
                      </TableRow>
                    ) : (
                      paginatedEvents.map((ev, idx) => {
                        const actualIdx = (realtimePage - 1) * realtimePageSize + idx;
                        let badgeColor: "default" | "secondary" | "destructive" | "outline" = "outline";
                        if (ev.tipo === "INICIO_JORNADA") badgeColor = "default";
                        else if (ev.tipo === "FIM_JORNADA") badgeColor = "destructive";
                        else if (ev.tipo === "ABASTECIMENTO") badgeColor = "secondary";
                        else if (ev.tipo === "TELEMETRIA_GPS") badgeColor = "outline";

                        const isChecked = selectedEvents.some(
                          x => x.timestamp === ev.timestamp && x.jornada_id === ev.jornada_id
                        );

                        const isRowInRange = (() => {
                          if (trackStartIdxRef.current === null || trackHoverIdx === null) return false;
                          const start = Math.min(trackStartIdxRef.current, trackHoverIdx);
                          const end = Math.max(trackStartIdxRef.current, trackHoverIdx);
                          return actualIdx >= start && actualIdx <= end;
                        })();

                        const rowBgColor = (() => {
                          if (isRowInRange) {
                            return dragSelectModeRef.current ? 'bg-blue-50/20' : 'bg-red-50/20';
                          }
                          return isChecked ? 'bg-blue-50/20' : '';
                        })();

                        const trackDotColor = (() => {
                          if (trackStartIdxRef.current === actualIdx) {
                            return dragSelectModeRef.current ? 'bg-emerald-500 scale-125 animate-pulse' : 'bg-rose-500 scale-125 animate-pulse';
                          }
                          if (isRowInRange) {
                            return dragSelectModeRef.current ? 'bg-blue-500 scale-110' : 'bg-rose-400 scale-110';
                          }
                          return isChecked ? 'bg-blue-500' : 'bg-slate-300 hover:bg-blue-400';
                        })();

                        const trackLineColor = (() => {
                          if (isRowInRange) {
                            return dragSelectModeRef.current ? 'bg-blue-500' : 'bg-rose-400';
                          }
                          return isChecked ? 'bg-blue-300' : 'bg-slate-200';
                        })();

                        return (
                          <TableRow 
                            key={actualIdx} 
                            className={`hover:bg-slate-50/50 transition-all duration-150 ${rowBgColor}`}
                          >
                            <TableCell className="w-[50px] relative select-none text-center p-0">
                              <div className={`absolute top-0 bottom-0 w-0.5 left-1/2 -translate-x-1/2 z-0 ${trackLineColor}`} />
                              <div 
                                className="relative z-10 flex justify-center items-center h-full min-h-[44px]"
                                onMouseDown={(e) => handleTrackMouseDown(e, actualIdx)}
                                onMouseEnter={() => handleTrackMouseEnter(actualIdx)}
                              >
                                <div
                                  className={`w-3.5 h-3.5 rounded-full border-2 border-white transition-all shadow-sm cursor-row-resize ${trackDotColor}`}
                                  title="Clique e arraste para selecionar faixa"
                                />
                              </div>
                            </TableCell>
                          <TableCell className="font-mono text-xs">
                            <div className="font-semibold text-slate-700">
                              {formatDateTime(ev.timestamp)}
                            </div>
                            {ev.rua ? (
                              <div className="text-[10px] text-slate-500 font-sans mt-0.5 max-w-[180px] truncate" title={ev.rua}>
                                {ev.rua}
                              </div>
                            ) : ev.tipo === 'TELEMETRIA_GPS' ? (
                              <div className="text-[10px] text-slate-400 font-sans italic mt-0.5">
                                Rua não identificada
                              </div>
                            ) : null}
                            {ev.lat && ev.lon && (
                              <div className="text-[9px] text-slate-400 font-mono mt-0.5">
                                Lat: {ev.lat.toFixed(5)}, Lon: {ev.lon.toFixed(5)}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="font-semibold text-slate-700">{ev.motorista_nome}</TableCell>
                          <TableCell className="font-mono text-xs">{ev.veiculo_id}</TableCell>
                          <TableCell>
                            <div className="flex flex-col">
                              <Badge variant={badgeColor} className="w-fit">{ev.tipo}</Badge>
                              {ev.detalhes && (
                                <span className="text-[10px] text-slate-400 mt-1 font-mono tracking-tighter">
                                  {ev.tipo === 'TELEMETRIA_GPS'
                                    ? ev.detalhes.split(' | ').filter((p: string) => !p.startsWith('Rua') && !p.startsWith('Lat:')).join(' | ')
                                    : ev.detalhes}
                                </span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="font-medium">{ev.km?.toFixed(1) ?? '—'} km</TableCell>
                          <TableCell className="text-right">
                            {ev.jornada_id && (
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteTelemetry(ev.jornada_id)}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50 p-1 h-8 w-8"
                                title="Apagar toda a telemetria desta jornada"
                              >
                                <Trash size={14} />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>

              {/* Controles de Paginação */}
              {filteredEvents.length > realtimePageSize && (
                <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-4">
                  <span className="text-xs text-slate-500">
                    Mostrando <strong>{((realtimePage - 1) * realtimePageSize) + 1}</strong> a <strong>{Math.min(realtimePage * realtimePageSize, filteredEvents.length)}</strong> de <strong>{filteredEvents.length}</strong> eventos
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={realtimePage === 1}
                      onClick={() => setRealtimePage(p => Math.max(1, p - 1))}
                      className="h-8 px-3 text-xs"
                    >
                      Anterior
                    </Button>
                    <span className="text-xs font-semibold px-2 text-slate-700">
                      Página {realtimePage} de {Math.ceil(filteredEvents.length / realtimePageSize)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={realtimePage >= Math.ceil(filteredEvents.length / realtimePageSize)}
                      onClick={() => setRealtimePage(p => Math.min(Math.ceil(filteredEvents.length / realtimePageSize), p + 1))}
                      className="h-8 px-3 text-xs"
                    >
                      Próxima
                    </Button>
                  </div>
                </div>
              )}
            </Card>

            {/* Painel do Mapa Lateral (Split Screen) */}
            {selectedEvents.length > 0 && (
              <Card className="lg:col-span-2 p-4 h-[600px] border border-slate-100 shadow-lg rounded-2xl flex flex-col gap-3 sticky top-6 self-start">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MapTrifold size={18} className="text-blue-600" />
                    <h3 className="text-sm font-bold text-slate-700">Roteamento dos Eventos</h3>
                  </div>
                  <Badge variant="outline" className="text-[10px] font-semibold">
                    {selectedRoutes.length} motorista(s) ativo(s)
                  </Badge>
                </div>

                <div className="w-full flex-1 min-h-0 bg-slate-50 rounded-xl overflow-hidden relative border border-slate-100">
                  {selectedRoutes.length > 0 ? (
                    <SelectedEventsMap routes={selectedRoutes} />
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center text-center p-6 bg-slate-50 text-slate-400">
                      <span className="text-xs font-semibold animate-pulse">Buscando telemetria correspondente...</span>
                    </div>
                  )}
                </div>
              </Card>
            )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'importar' && (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Importação de Relatórios de Ganhos</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Importar dados de faturamento externo da Uber e 99 para cruzamento e auditoria da telemetria
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="md:col-span-2 p-8 border-2 border-dashed border-slate-200 hover:border-slate-300 transition-all rounded-2xl flex flex-col items-center justify-center text-center gap-4 bg-slate-50/50">
              <div className="p-4 bg-blue-50 text-blue-500 rounded-full">
                <FileArrowUp size={36} />
              </div>
              <div className="space-y-1 max-w-sm">
                <h4 className="text-sm font-semibold text-slate-800">Selecione o Extrato de Ganhos</h4>
                <p className="text-xs text-muted-foreground">
                  Arraste e solte o arquivo CSV ou PDF oficial do seu aplicativo ou clique para navegar
                </p>
              </div>
              <input type="file" className="hidden" id="file-uploader" disabled />
              <Button onClick={() => document.getElementById('file-uploader')?.click()} disabled className="mt-2 text-xs">
                Selecionar Arquivo
              </Button>
            </Card>

            <Card className="p-6 border border-slate-100 shadow-sm rounded-2xl space-y-4">
              <div className="flex items-center gap-2.5 text-amber-600 bg-amber-50 px-3 py-2 rounded-xl border border-amber-100">
                <Warning size={20} weight="fill" />
                <span className="text-xs font-bold uppercase tracking-wide">Planejamento [TODO]</span>
              </div>
              
              <div className="space-y-3 text-xs leading-relaxed text-slate-600">
                <p className="font-semibold text-slate-800">Integração dos Extratos de Apps:</p>
                <p>
                  Esta seção conterá o parser automático dos extratos mensais e diários exportados pelos motoristas. 
                </p>
                <p>
                  O motorista carrega o relatório de rendimentos, e o algoritmo de backend mapeará as coordenadas de cada corrida (`id_viagem`) para bater com as posições registradas no GPS do veículo da frota no mesmo instante.
                </p>
                <div className="flex items-center gap-2 text-emerald-600 font-semibold pt-1">
                  <ShieldCheck size={16} weight="fill" />
                  <span>Auditoria e Comparação de Km/Ganhos</span>
                </div>
              </div>
            </Card>
          </div>

          <Card className="p-6">
            <h3 className="text-sm font-bold text-slate-700 mb-4 uppercase tracking-wider">Histórico de Importações Recentes</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data de Importação</TableHead>
                  <TableHead>Aplicativo</TableHead>
                  <TableHead>Arquivo</TableHead>
                  <TableHead>Corridas Mapeadas</TableHead>
                  <TableHead>Valor Total</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow className="opacity-60">
                  <TableCell className="font-mono text-xs">27/06/2026 14:32</TableCell>
                  <TableCell><Badge variant="outline">UBER</Badge></TableCell>
                  <TableCell className="font-mono text-xs">extrato_uber_carlos_junio.csv</TableCell>
                  <TableCell>14 corridas</TableCell>
                  <TableCell>{formatCurrency(384.20)}</TableCell>
                  <TableCell><Badge variant="default" className="bg-emerald-500">Mapeado</Badge></TableCell>
                </TableRow>
                <TableRow className="opacity-60">
                  <TableCell className="font-mono text-xs">26/06/2026 18:15</TableCell>
                  <TableCell><Badge variant="outline">99APP</Badge></TableCell>
                  <TableCell className="font-mono text-xs">relatorio_99_bruno.xlsx</TableCell>
                  <TableCell>9 corridas</TableCell>
                  <TableCell>{formatCurrency(245.90)}</TableCell>
                  <TableCell><Badge variant="default" className="bg-emerald-500">Mapeado</Badge></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </Card>
        </div>
      )}
    </div>
  );
}
