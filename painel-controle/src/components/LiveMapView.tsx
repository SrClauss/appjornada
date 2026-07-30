import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Jornada } from '@/lib/types';

interface LiveMapViewProps {
  jornadas: Jornada[];
  onSelectJornada?: (jornada: Jornada) => void;
}

export function LiveMapView({ jornadas, onSelectJornada }: LiveMapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    if (!mapRef.current) {
      // Centro inicial: Vitória / Grande Vitória - ES (exemplo padrão) ou centro dos veículos
      const map = L.map(containerRef.current, {
        zoomControl: true,
      }).setView([-20.3155, -40.3128], 12);

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = map;
    }

    const map = mapRef.current;

    // Limpa marcadores anteriores
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const bounds = L.latLngBounds([]);

    // Adiciona marcadores para jornadas com localização de telemetria ou inicial
    jornadas.forEach((j) => {
      let lat: number | undefined;
      let lon: number | undefined;

      if (j.segmentos_rota && j.segmentos_rota.length > 0) {
        // Tenta pegar última posição da polilinha se houver
      }

      const locObj =
        (j as any).localizacao_atual ||
        (j as any).localizacao_inicial ||
        (j as any).localizacao_inicio ||
        (j as any).localizacao;

      if (locObj?.lat !== undefined && locObj?.lon !== undefined && Number(locObj.lat) !== 0 && Number(locObj.lon) !== 0) {
        lat = Number(locObj.lat);
        lon = Number(locObj.lon);
      } else if (locObj?.latitude !== undefined && locObj?.longitude !== undefined) {
        lat = Number(locObj.latitude);
        lon = Number(locObj.longitude);
      }

      // Se não tiver lat/lon direta, ignora exibição deste marcador no mapa
      if (!lat || !lon) {
        return;
      }

      const statusColor = j.status === 'EM_ANDAMENTO' ? '#10B981' : j.status === 'EM_PAUSA' ? '#F59E0B' : '#6366F1';
      
      const customIcon = L.divIcon({
        className: 'custom-vehicle-marker',
        html: `
          <div style="
            background-color: ${statusColor};
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 12px ${statusColor};
            border: 2px solid white;
            color: white;
            font-weight: bold;
          ">
            🚗
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([lat, lon], { icon: customIcon }).addTo(map);

      const popupContent = `
        <div style="color: #0f172a; font-family: sans-serif; padding: 4px;">
          <h4 style="margin:0 0 4px 0; font-weight:bold; font-size:14px;">${j.motorista_nome || 'Motorista'}</h4>
          <p style="margin:0; font-size:12px; color:#475569;">Veículo: <strong>${j.veiculo_id}</strong></p>
          <p style="margin:2px 0; font-size:12px; color:#475569;">Status: <span style="color:${statusColor}; font-weight:bold;">${j.status}</span></p>
          ${j.km?.rodados ? `<p style="margin:2px 0; font-size:12px;">Rodados: <strong>${j.km.rodados} km</strong></p>` : ''}
          ${j.score_auditoria ? `<p style="margin:4px 0 0 0; font-size:11px; font-weight:bold; color:${j.score_auditoria.nivel_risco === 'VERDE' ? '#10B981' : j.score_auditoria.nivel_risco === 'AMARELO' ? '#D97706' : '#EF4444'}">Auditoria: ${j.score_auditoria.nivel_risco} (${j.score_auditoria.score_risco} pts)</p>` : ''}
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', () => {
        if (onSelectJornada) onSelectJornada(j);
      });

      markersRef.current.push(marker);
      bounds.extend([lat, lon]);
    });

    if (markersRef.current.length === 1 && bounds.isValid()) {
      const center = bounds.getCenter();
      map.setView([center.lat, center.lng], 14);
    } else if (markersRef.current.length > 1 && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
  }, [jornadas]);

  return (
    <div className="relative w-full h-[380px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-[#0d1117]">
      <div ref={containerRef} className="w-full h-full z-10" />

      {/* Overlay de Legenda */}
      <div className="absolute bottom-3 left-3 z-[400] bg-slate-900/90 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-800 flex items-center gap-4 text-xs text-slate-300">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10B981]"></span>
          <span>Rodando</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_8px_#F59E0B]"></span>
          <span>Em Pausa</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
          <span>Aberta</span>
        </div>
      </div>
    </div>
  );
}
