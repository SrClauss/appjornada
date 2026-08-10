  import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Jornada, BaseOperacao } from '@/lib/types';
import type { TelemetriaPoint } from './DriverReplayOverlay';

interface LiveMapViewProps {
  jornadas: Jornada[];
  bases?: BaseOperacao[];
  baseFoco?: BaseOperacao | null;
  selectedJornadaId?: string | null;
  onSelectJornada?: (jornada: Jornada) => void;
  onStartReplay?: (jornada: Jornada) => void;
  onShowCompleteRoute?: (jornada: Jornada) => void;
  // Replay Mode Props
  replayMode?: boolean;
  replayPoints?: TelemetriaPoint[];
  osrmRouteCoords?: [number, number][];
  currentReplayIndex?: number;
  followVehicle?: boolean;
  onFitCompleteRoute?: () => void;
}

export function LiveMapView({ 
  jornadas, 
  bases = [], 
  baseFoco, 
  selectedJornadaId,
  onSelectJornada,
  onStartReplay,
  onShowCompleteRoute,
  replayMode = false,
  replayPoints = [],
  osrmRouteCoords = [],
  currentReplayIndex = 0,
  followVehicle = true,
  onFitCompleteRoute,
}: LiveMapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const replayPolylineOsrmRef = useRef<L.Polyline | null>(null);
  const replayPolylineGpsRef = useRef<L.Polyline | null>(null);
  const replayVehicleMarkerRef = useRef<L.Marker | null>(null);
  const replayGpsMarkersRef = useRef<L.CircleMarker[]>([]);
  
  const isInitialFitRef = useRef<boolean>(false);
  const prevBaseFocoRef = useRef<BaseOperacao | null | undefined>(baseFoco);
  const prevSelectedJornadaIdRef = useRef<string | null | undefined>(selectedJornadaId);
  const initialRouteFittedRef = useRef<boolean>(false);

  const basePrincipal = bases.find((b) => b.is_principal) || bases[0];
  const targetBase = baseFoco || basePrincipal;

  const fallbackLat = targetBase?.lat ?? -20.3155;
  const fallbackLon = targetBase?.lon ?? -40.3128;
  const fallbackZoom = targetBase?.zoom_padrao ?? 12;

  const centralizarMapa = () => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const bounds = L.latLngBounds([]);

    markersRef.current.forEach((m) => {
      bounds.extend(m.getLatLng());
    });

    if (baseFoco && baseFoco.lat && baseFoco.lon) {
      map.setView([baseFoco.lat, baseFoco.lon], baseFoco.zoom_padrao || 13);
    } else if (bounds.isValid() && markersRef.current.length > 0) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    } else if (targetBase && targetBase.lat && targetBase.lon) {
      map.setView([targetBase.lat, targetBase.lon], targetBase.zoom_padrao || 13);
    }
  };

  const fitCompleteRoute = () => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    const bounds = L.latLngBounds([]);

    if (osrmRouteCoords.length > 0) {
      osrmRouteCoords.forEach((c) => bounds.extend(c));
    } else if (replayPoints.length > 0) {
      replayPoints.forEach((p) => bounds.extend([p.lat, p.lng]));
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  };

  // Initialize Map
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
  }, [fallbackLat, fallbackLon, fallbackZoom]);

  // Handle Standard Live Markers
  useEffect(() => {
    if (!mapRef.current || replayMode) return;
    const map = mapRef.current;

    // Clear live markers
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];

    const bounds = L.latLngBounds([]);

    // Base Markers
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
        bounds.extend([b.lat, b.lon]);
      }
    });

    // Driver Markers
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

      if (!lat || !lon) return;

      const isSelected = selectedJornadaId === (j.id || (j as any)._id);

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
            background-color: ${isSelected ? '#00f0ff' : statusColor};
            width: ${isSelected ? '38px' : '32px'};
            height: ${isSelected ? '38px' : '32px'};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: ${isSelected ? '0 0 20px #00f0ff' : `0 0 12px ${statusColor}`};
            border: ${isSelected ? '3px solid white' : '2px solid white'};
            color: white;
            font-weight: bold;
            transition: all 0.3s ease;
          ">
            🚗
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const marker = L.marker([lat, lon], { icon: customIcon }).addTo(map);

      const jIdStr = j.id || (j as any)._id;

      const popupContent = `
        <div style="color: #0f172a; font-family: sans-serif; padding: 6px; min-width: 200px;">
          <h4 style="margin:0 0 4px 0; font-weight:bold; font-size:14px; color:#0f172a;">${j.motorista_nome || 'Motorista'}</h4>
          <p style="margin:0; font-size:12px; color:#475569;">Veículo: <strong style="color:#0f172a;">${j.veiculo_id}</strong></p>
          <p style="margin:2px 0; font-size:12px; color:#475569;">Status: <span style="color:${statusColor}; font-weight:bold;">${j.status}</span></p>
          ${j.km?.rodados ? `<p style="margin:2px 0; font-size:12px;">Rodados: <strong>${j.km.rodados} km</strong></p>` : ''}
          <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 4px;">
            <button id="btn-popup-route-${jIdStr}" style="
              background: #0284c7; color: white; border: none; padding: 5px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; cursor: pointer;
            ">🗺️ Ver Rota Completa</button>
            <button id="btn-popup-replay-${jIdStr}" style="
              background: #4f46e5; color: white; border: none; padding: 5px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; cursor: pointer;
            ">🎥 Refazer Caminho (Replay)</button>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent);
      
      marker.on('popupopen', () => {
        const btnRoute = document.getElementById(`btn-popup-route-${jIdStr}`);
        if (btnRoute && onShowCompleteRoute) {
          btnRoute.onclick = () => {
            onShowCompleteRoute(j);
            marker.closePopup();
          };
        }

        const btnReplay = document.getElementById(`btn-popup-replay-${jIdStr}`);
        if (btnReplay && onStartReplay) {
          btnReplay.onclick = () => {
            onStartReplay(j);
            marker.closePopup();
          };
        }
      });

      marker.on('click', () => {
        if (onSelectJornada) onSelectJornada(j);
      });

      markersRef.current.push(marker);
      bounds.extend([lat, lon]);

      // If this driver is selected, zoom directly to their coordinates!
      if (isSelected && map) {
        map.setView([lat, lon], 16, { animate: true });
      }
    });

    // Fit map bounds on initial load
    const baseFocoMudou = prevBaseFocoRef.current !== baseFoco;
    prevBaseFocoRef.current = baseFoco;
    prevSelectedJornadaIdRef.current = selectedJornadaId;

    if (!isInitialFitRef.current || baseFocoMudou) {
      centralizarMapa();
      isInitialFitRef.current = true;
    }
  }, [jornadas, bases, baseFoco, selectedJornadaId, replayMode]);

  // Handle Replay Mode Layer rendering
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    // Clear Replay Layers when leaving Replay Mode
    if (!replayMode) {
      if (replayPolylineOsrmRef.current) {
        replayPolylineOsrmRef.current.remove();
        replayPolylineOsrmRef.current = null;
      }
      if (replayPolylineGpsRef.current) {
        replayPolylineGpsRef.current.remove();
        replayPolylineGpsRef.current = null;
      }
      if (replayVehicleMarkerRef.current) {
        replayVehicleMarkerRef.current.remove();
        replayVehicleMarkerRef.current = null;
      }
      replayGpsMarkersRef.current.forEach((m) => m.remove());
      replayGpsMarkersRef.current = [];
      initialRouteFittedRef.current = false;
      return;
    }

    // Hide live markers during replay
    markersRef.current.forEach((m) => m.remove());

    // 1. Draw Raw GPS Polyline
    if (replayPoints.length > 0 && !replayPolylineGpsRef.current) {
      const gpsLatLngs = replayPoints.map((p) => [p.lat, p.lng] as [number, number]);
      replayPolylineGpsRef.current = L.polyline(gpsLatLngs, {
        color: '#f59e0b',
        weight: 3,
        opacity: 0.6,
        dashArray: '6, 8',
      }).addTo(map);

      // Raw GPS Dots
      replayGpsMarkersRef.current.forEach((m) => m.remove());
      replayGpsMarkersRef.current = [];
      replayPoints.forEach((p) => {
        const circle = L.circleMarker([p.lat, p.lng], {
          radius: 3,
          color: '#f59e0b',
          fillColor: '#fbbf24',
          fillOpacity: 0.7,
          weight: 1,
        }).addTo(map);
        replayGpsMarkersRef.current.push(circle);
      });
    }

    // 2. Draw OSRM Matched Route Polyline (Cyan Glow)
    if (osrmRouteCoords.length > 0) {
      if (replayPolylineOsrmRef.current) {
        replayPolylineOsrmRef.current.setLatLngs(osrmRouteCoords);
      } else {
        replayPolylineOsrmRef.current = L.polyline(osrmRouteCoords, {
          color: '#00f0ff',
          weight: 5,
          opacity: 0.9,
          lineCap: 'round',
          lineJoin: 'round',
        }).addTo(map);
      }
    }

    // Fit complete route on initial load of replay mode
    if (!initialRouteFittedRef.current) {
      fitCompleteRoute();
      initialRouteFittedRef.current = true;
    }

    // 3. Update Vehicle Pulsing Position
    if (replayPoints.length > 0) {
      const currentPoint = replayPoints[currentReplayIndex] || replayPoints[0];
      const pos: [number, number] = [currentPoint.lat, currentPoint.lng];

      if (!replayVehicleMarkerRef.current) {
        const vehicleIcon = L.divIcon({
          className: 'replay-vehicle-marker',
          html: `
            <div style="
              width: 28px;
              height: 28px;
              background-color: #3b82f6;
              border: 3px solid white;
              border-radius: 50%;
              box-shadow: 0 0 20px #3b82f6, 0 0 35px rgba(59, 130, 246, 0.7);
              display: flex;
              align-items: center;
              justify-content: center;
            ">
              <div style="width: 8px; height: 8px; background: white; border-radius: 50%;"></div>
            </div>
          `,
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        });

        replayVehicleMarkerRef.current = L.marker(pos, { icon: vehicleIcon }).addTo(map);
      } else {
        replayVehicleMarkerRef.current.setLatLng(pos);
        if (followVehicle) {
          map.panTo(pos, { animate: true });
        }
      }
    }
  }, [replayMode, replayPoints, osrmRouteCoords, currentReplayIndex, followVehicle]);

  return (
    <div className="relative w-full h-[460px] md:h-[520px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-[#0d1117]">
      <div ref={containerRef} className="w-full h-full z-10" />

      {/* Buttons top right */}
      {replayMode ? (
        <button
          onClick={fitCompleteRoute}
          className="absolute top-3 right-3 z-[400] bg-slate-900/90 hover:bg-slate-800 text-cyan-300 px-3 py-1.5 rounded-xl border border-cyan-500/40 text-xs font-bold flex items-center gap-1.5 shadow-lg backdrop-blur-md transition-all active:scale-95"
        >
          🗺️ Ver Rota Completa
        </button>
      ) : (
        <button
          onClick={centralizarMapa}
          className="absolute top-3 right-3 z-[400] bg-slate-900/90 hover:bg-slate-800 text-white px-3 py-1.5 rounded-xl border border-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-lg backdrop-blur-md transition-all active:scale-95"
        >
          🎯 Centralizar Visão
        </button>
      )}

      {/* Legend Overlay */}
      <div className="absolute bottom-3 left-3 z-[400] bg-slate-900/90 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-800 flex items-center gap-4 text-xs text-slate-300 flex-wrap shadow-xl">
        {replayMode ? (
          <>
            <div className="flex items-center gap-1.5">
              <span className="w-4 h-1 rounded bg-[#00f0ff] shadow-[0_0_8px_#00f0ff]"></span>
              <span className="font-semibold text-cyan-300">Rota OSRM Encaixada</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-4 h-1 rounded bg-[#f59e0b]"></span>
              <span>Pontos Brutos GPS</span>
            </div>
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
}
