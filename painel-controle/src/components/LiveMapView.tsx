import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Jornada, BaseOperacao } from '@/lib/types';

interface LiveMapViewProps {
  jornadas: Jornada[];
  bases?: BaseOperacao[];
  baseFoco?: BaseOperacao | null;
  onSelectJornada?: (jornada: Jornada) => void;
}

export function LiveMapView({ jornadas, bases = [], baseFoco, onSelectJornada }: LiveMapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);

  const basePrincipal = bases.find((b) => b.is_principal) || bases[0];
  const targetBase = baseFoco || basePrincipal;

  const fallbackLat = targetBase?.lat ?? -20.3155;
  const fallbackLon = targetBase?.lon ?? -40.3128;
  const fallbackZoom = targetBase?.zoom_padrao ?? 12;

  useEffect(() => {
    if (!containerRef.current) return;

    if (!mapRef.current) {
      const map = L.map(containerRef.current, {
        zoomControl: true,
      }).setView([fallbackLat, fallbackLon], fallbackZoom);

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

    // Marcadores das Bases de Operações
    bases.forEach((b) => {
      if (b.lat && b.lon) {
        const baseIcon = L.divIcon({
          className: 'custom-base-marker',
          html: `
            <div style="
              background-color: #3b82f6;
              width: 28px;
              height: 28px;
              border-radius: 8px;
              display: flex;
              align-items: center;
              justify-content: center;
              box-shadow: 0 0 10px #3b82f6;
              border: 2px solid white;
              color: white;
              font-size: 14px;
            ">
              🏢
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        const bMarker = L.marker([b.lat, b.lon], { icon: baseIcon }).addTo(map);
        bMarker.bindPopup(`
          <div style="color: #0f172a; font-family: sans-serif; padding: 4px;">
            <h4 style="margin:0 0 4px 0; font-weight:bold; font-size:14px;">🏢 ${b.nome}</h4>
            <p style="margin:0; font-size:12px; color:#475569;">${b.cidade || ''} ${b.estado ? `- ${b.estado}` : ''}</p>
            ${b.is_principal ? '<span style="color:#3b82f6; font-weight:bold; font-size:11px;">★ Base Principal</span>' : ''}
          </div>
        `);
        markersRef.current.push(bMarker);
      }
    });

    // Marcadores dos Motoristas
    jornadas.forEach((j) => {
      let lat: number | undefined;
      let lon: number | undefined;

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

      if (!lat || !lon) {
        return;
      }

      const statusColor =
        j.status === 'EM_ANDAMENTO'
          ? '#10B981'
          : j.status === 'EM_PAUSA'
          ? '#F59E0B'
          : j.status === 'ABERTA'
          ? '#6366F1'
          : '#64748B';
      
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

    if (baseFoco) {
      map.setView([baseFoco.lat, baseFoco.lon], baseFoco.zoom_padrao || 13);
    } else if (markersRef.current.length === 1 && bounds.isValid()) {
      const center = bounds.getCenter();
      map.setView([center.lat, center.lng], 14);
    } else if (markersRef.current.length > 1 && bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    } else if (targetBase) {
      map.setView([targetBase.lat, targetBase.lon], targetBase.zoom_padrao || 13);
    }
  }, [jornadas, bases, baseFoco, fallbackLat, fallbackLon, fallbackZoom]);

  return (
    <div className="relative w-full h-[380px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-[#0d1117]">
      <div ref={containerRef} className="w-full h-full z-10" />

      {/* Overlay de Legenda */}
      <div className="absolute bottom-3 left-3 z-[400] bg-slate-900/90 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-800 flex items-center gap-4 text-xs text-slate-300 flex-wrap">
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
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
          <span>Encerrada</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px]">🏢 Base Operacional</span>
        </div>
      </div>
    </div>
  );
}
