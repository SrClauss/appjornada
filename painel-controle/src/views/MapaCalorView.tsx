import React, { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Flame, DownloadSimple, CurrencyDollar, MapPin, Trophy, Calendar } from '@phosphor-icons/react';
import api from '@/lib/api';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import html2canvas from 'html2canvas';

interface PontoHeatmap {
  lat: number;
  lon: number;
  valor: number;
  plataforma: string;
  tipo: string;
  data?: string;
}

interface MapaCalorResponse {
  periodo: string;
  data_inicio: string;
  data_fim: string;
  total_pontos: number;
  total_faturamento: number;
  ticket_medio: number;
  maior_ticket: number;
  pontos: PontoHeatmap[];
}

interface MotoristaOption {
  id: string;
  nome: string;
}

export function MapaCalorView() {
  const [periodo, setPeriodo] = useState<'diario' | 'semanal' | 'mensal'>('mensal');
  const [selectedMotorista, setSelectedMotorista] = useState<string>('todos');
  const [dataReferencia, setDataReferencia] = useState<string>(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });

  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [data, setData] = useState<MapaCalorResponse | null>(null);
  const [motoristas, setMotoristas] = useState<MotoristaOption[]>([]);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);
  const cardMapWrapperRef = useRef<HTMLDivElement>(null);

  // Carregar lista de motoristas para o filtro
  useEffect(() => {
    async function loadMotoristas() {
      try {
        const { data: res } = await api.get('/users?role=MOTORISTA');
        if (Array.isArray(res)) {
          setMotoristas(res.map((m: any) => ({ id: m.id || m._id, nome: m.nome || m.email })));
        } else if (res && Array.isArray(res.items)) {
          setMotoristas(res.items.map((m: any) => ({ id: m.id || m._id, nome: m.nome || m.email })));
        }
      } catch (err) {
        console.error('Erro ao carregar motoristas:', err);
      }
    }
    loadMotoristas();
  }, []);

  // Carregar dados do Mapa de Calor
  const fetchMapaCalor = async () => {
    setLoading(true);
    try {
      const params: any = { periodo, data_referencia: dataReferencia };
      if (selectedMotorista !== 'todos') {
        params.motorista_id = selectedMotorista;
      }
      const { data: res } = await api.get('/gps/mapa-calor', { params });
      setData(res);
    } catch (err) {
      console.error('Erro ao buscar dados do mapa de calor:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMapaCalor();
  }, [periodo, selectedMotorista, dataReferencia]);

  // Inicialização do Mapa Leaflet
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapRef.current) {
      const map = L.map(mapContainerRef.current).setView([-20.3155, -40.3128], 13);
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19,
      }).addTo(map);

      const layerGroup = L.layerGroup().addTo(map);
      mapRef.current = map;
      layerGroupRef.current = layerGroup;
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Renderizar os pontos ponderados no Mapa
  useEffect(() => {
    const map = mapRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    if (!data || !data.pontos || data.pontos.length === 0) return;

    let validCount = 0;
    const bounds = L.latLngBounds([]);

    data.pontos.forEach((p) => {
      let lat = Number(p.lat);
      let lon = Number(p.lon);
      if (!lat || !lon) return;

      // Inversão se lat/lon estiverem trocados
      if (Math.abs(lat) > 34.0 && Math.abs(lon) <= 34.0) {
        const temp = lat;
        lat = lon;
        lon = temp;
      }

      // Validar limites geográficos do Brasil (Vitória / ES)
      if (lat < -34.0 || lat > 5.0 || lon < -75.0 || lon > -30.0) return;

      validCount++;
      const valor = p.valor || 0;
      let color = '#10b981'; // Verde (< R$ 15)
      if (valor >= 100) {
        color = '#ec4899'; // Magenta/Pink (>= R$ 100)
      } else if (valor >= 60) {
        color = '#ef4444'; // Vermelho (R$ 60 - R$ 100)
      } else if (valor >= 30) {
        color = '#f59e0b'; // Laranja/Amber (R$ 30 - R$ 60)
      } else if (valor >= 15) {
        color = '#06b6d4'; // Ciano/Azul (R$ 15 - R$ 30)
      }

      // Raio proporcional ao valor
      const radius = Math.max(8, Math.min(26, Math.round(valor / 4.0)));

      const circle = L.circleMarker([lat, lon], {
        radius,
        fillColor: color,
        color: '#ffffff',
        weight: 1.5,
        opacity: 0.9,
        fillOpacity: 0.65,
      }).addTo(layerGroup);

      circle.bindPopup(`
        <div style="font-family: sans-serif; font-size: 13px; padding: 4px;">
          <strong style="font-size: 15px; color: ${color};">R$ ${valor.toFixed(2).replace('.', ',')}</strong><br/>
          <span>Plataforma: <b>${p.plataforma}</b></span><br/>
          ${p.data ? `<span>Data: <b>${p.data}</b></span>` : ''}
        </div>
      `);

      bounds.extend([lat, lon]);
    });

    if (validCount > 0 && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    } else {
      map.setView([-20.3155, -40.3128], 13);
    }
  }, [data]);

  // Exportar mapa como imagem (PNG)
  const handleExportPNG = async () => {
    if (!cardMapWrapperRef.current) return;
    setExporting(true);
    try {
      const canvas = await html2canvas(cardMapWrapperRef.current, {
        useCORS: true,
        allowTaint: true,
        background: '#0f172a',
      });
      const link = document.createElement('a');
      link.download = `mapa-de-calor-ticket-${periodo}-${dataReferencia}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (e) {
      console.error('Erro ao exportar mapa em PNG:', e);
      alert('Erro ao gerar imagem do mapa.');
    } finally {
      setExporting(false);
    }
  };

  const formatCurrency = (val: number) =>
    `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="p-6 space-y-6 bg-slate-950 min-h-screen text-slate-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Flame className="w-8 h-8 text-amber-500 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight text-white">Mapa de Calor (Raio de Maior Ticket)</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Visualização de concentração geográfica de corridas ponderada pelo valor cobrado (R$).
          </p>
        </div>
        <Button
          onClick={handleExportPNG}
          disabled={exporting || loading}
          className="bg-amber-600 hover:bg-amber-500 text-white font-semibold flex items-center gap-2 shadow-lg shadow-amber-900/30"
        >
          <DownloadSimple className="w-5 h-5" />
          {exporting ? 'Gerando Imagem...' : 'Exportar Mapa (PNG)'}
        </Button>
      </div>

      {/* Barra de Filtros */}
      <Card className="p-4 bg-slate-900 border-slate-800 flex flex-wrap items-center gap-4">
        <div className="space-y-1">
          <Label className="text-xs text-slate-400">Período</Label>
          <Select value={periodo} onValueChange={(val: any) => setPeriodo(val)}>
            <SelectTrigger className="w-40 bg-slate-950 border-slate-800 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="diario">Hoje / Diário</SelectItem>
              <SelectItem value="semanal">Esta Semana</SelectItem>
              <SelectItem value="mensal">Este Mês</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs text-slate-400">Data de Referência</Label>
          <Input
            type="date"
            value={dataReferencia}
            onChange={(e) => setDataReferencia(e.target.value)}
            className="w-44 bg-slate-950 border-slate-800 text-white"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs text-slate-400">Motorista</Label>
          <Select value={selectedMotorista} onValueChange={setSelectedMotorista}>
            <SelectTrigger className="w-52 bg-slate-950 border-slate-800 text-white">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos os Motoristas</SelectItem>
              {motoristas.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </Card>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4 bg-slate-900 border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl">
            <MapPin className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Corridas Mapeadas</p>
            <p className="text-2xl font-bold text-white">{data?.total_pontos ?? 0}</p>
          </div>
        </Card>

        <Card className="p-4 bg-slate-900 border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
            <CurrencyDollar className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Total Faturado</p>
            <p className="text-2xl font-bold text-emerald-400">{formatCurrency(data?.total_faturamento ?? 0)}</p>
          </div>
        </Card>

        <Card className="p-4 bg-slate-900 border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl">
            <Flame className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Ticket Médio</p>
            <p className="text-2xl font-bold text-purple-300">{formatCurrency(data?.ticket_medio ?? 0)}</p>
          </div>
        </Card>

        <Card className="p-4 bg-slate-900 border-slate-800 flex items-center gap-4">
          <div className="p-3 bg-pink-500/10 text-pink-400 rounded-xl">
            <Trophy className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-medium">Maior Ticket</p>
            <p className="text-2xl font-bold text-pink-400">{formatCurrency(data?.maior_ticket ?? 0)}</p>
          </div>
        </Card>
      </div>

      {/* Container do Mapa */}
      <Card ref={cardMapWrapperRef} className="p-4 bg-slate-900 border-slate-800 relative overflow-hidden">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Concentração Geográfica</span>
            {loading && <span className="text-xs text-amber-400 animate-pulse">Carregando dados...</span>}
          </div>

          {/* Legenda de Gradiente de Ticket */}
          <div className="hidden sm:flex items-center gap-3 text-xs bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800">
            <span className="text-slate-400">Raio de Ticket:</span>
            <span className="flex items-center gap-1 text-emerald-400"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>&lt;R$15</span>
            <span className="flex items-center gap-1 text-cyan-400"><span className="w-2.5 h-2.5 rounded-full bg-cyan-500"></span>R$15-30</span>
            <span className="flex items-center gap-1 text-amber-400"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>R$30-60</span>
            <span className="flex items-center gap-1 text-orange-400"><span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span>R$60-100</span>
            <span className="flex items-center gap-1 text-pink-400"><span className="w-2.5 h-2.5 rounded-full bg-pink-500"></span>&gt;R$100</span>
          </div>
        </div>

        <div className="h-[580px] w-full rounded-xl overflow-hidden border border-slate-800">
          <div ref={mapContainerRef} className="h-full w-full" />
        </div>
      </Card>
    </div>
  );
}
