import React from 'react';
import { 
  Play, 
  Pause, 
  ArrowClockwise, 
  Crosshair, 
  NavigationArrow, 
  MapPin, 
  Clock, 
  Pulse, 
  MapTrifold,
  X 
} from '@phosphor-icons/react';
import { Badge } from '@/components/ui/badge';
import type { Jornada } from '@/lib/types';

export interface TelemetriaPoint {
  id?: string;
  timestamp: string;
  lat: number;
  lng: number;
  distancia_ultima_m?: number;
  status?: string;
  rua?: string;
}

interface DriverReplayOverlayProps {
  jornada: Jornada;
  telemetriaPoints: TelemetriaPoint[];
  currentIndex: number;
  isPlaying: boolean;
  speed: number;
  followVehicle: boolean;
  distanciaOsrmKm: number;
  distanciaGpsKm: number;
  onIndexChange: (index: number) => void;
  onTogglePlay: () => void;
  onRestart: () => void;
  onToggleFollow: () => void;
  onFitCompleteRoute: () => void;
  onSpeedChange: (speed: number) => void;
  onClose: () => void;
}

export function DriverReplayOverlay({
  jornada,
  telemetriaPoints,
  currentIndex,
  isPlaying,
  speed,
  followVehicle,
  distanciaOsrmKm,
  distanciaGpsKm,
  onIndexChange,
  onTogglePlay,
  onRestart,
  onToggleFollow,
  onFitCompleteRoute,
  onSpeedChange,
  onClose,
}: DriverReplayOverlayProps) {
  const currentPoint = telemetriaPoints[currentIndex] || telemetriaPoints[0];
  const totalPoints = telemetriaPoints.length;

  const formatTimeStr = (iso?: string) => {
    if (!iso) return '--:--:--';
    try {
      let cleaned = iso.trim().replace(' ', 'T');
      if (!cleaned.endsWith('Z') && !/[+-]\d{2}:?\d{2}$/.test(cleaned)) {
        cleaned += 'Z';
      }
      return new Date(cleaned).toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return iso;
    }
  };

  const startTimeStr = telemetriaPoints.length > 0 ? formatTimeStr(telemetriaPoints[0].timestamp) : '--:--';
  const endTimeStr = telemetriaPoints.length > 0 ? formatTimeStr(telemetriaPoints[telemetriaPoints.length - 1].timestamp) : '--:--';

  const isConduzindo = currentPoint?.status === 'CONDUZINDO' || currentPoint?.status === 'EM_MOVIMENTO';

  return (
    <div className="w-full bg-[#0d1117]/95 backdrop-blur-xl border border-sky-500/40 rounded-2xl p-4 shadow-2xl shadow-sky-950/40 flex flex-col gap-3.5 mb-3 transition-all">
      {/* Line 1: Header Driver Stats & Close Button */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-sky-500/30 shrink-0">
            🚗
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-bold text-white text-base truncate">
                {jornada.motorista_nome || 'Motorista'}
              </h3>
              <Badge variant="outline" className="bg-sky-500/10 border-sky-500/30 text-sky-400 text-[10px] font-mono">
                {jornada.veiculo_id}
              </Badge>
              <Badge 
                variant="outline" 
                className={`text-[10px] uppercase font-bold tracking-wider ${
                  isConduzindo
                    ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                }`}
              >
                {currentPoint?.status || 'CONDUZINDO'}
              </Badge>
            </div>
            <p className="text-slate-300 text-xs truncate mt-0.5 font-medium flex items-center gap-1.5">
              <MapPin size={14} className="text-sky-400 shrink-0" />
              <span>{currentPoint?.rua || 'Via não identificada'}</span>
            </p>
          </div>
        </div>

        {/* Metrics Badge Group */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-slate-300 font-mono text-[11px] bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800 shrink-0">
            <div className="flex items-center gap-1">
              <NavigationArrow size={14} className="text-cyan-400" />
              <span>OSRM: <strong className="text-cyan-300 font-bold">{distanciaOsrmKm.toFixed(1)} km</strong></span>
            </div>
            <span className="text-slate-700">|</span>
            <div>
              <span>GPS: <strong className="text-amber-400 font-bold">{distanciaGpsKm.toFixed(1)} km</strong></span>
            </div>
            <span className="text-slate-700">|</span>
            <div className="flex items-center gap-1">
              <Pulse size={14} className="text-emerald-400" />
              <span>{currentIndex + 1}/{totalPoints} pts</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-300 border border-slate-700 transition-all shrink-0"
            title="Fechar Replay"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Line 2: Timeline Slider */}
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono font-semibold text-sky-400 min-w-[65px]">
          {formatTimeStr(currentPoint?.timestamp)}
        </span>
        
        <input
          type="range"
          min="0"
          max={Math.max(0, totalPoints - 1)}
          value={currentIndex}
          onChange={(e) => onIndexChange(Number(e.target.value))}
          className="flex-1 h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500 hover:accent-sky-400 transition-all"
        />

        <span className="text-xs font-mono text-slate-400 min-w-[65px] text-right">
          {endTimeStr}
        </span>
      </div>

      {/* Line 3: Controls Buttons Row */}
      <div className="flex items-center justify-between gap-2 flex-wrap pt-1">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={onFitCompleteRoute}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-500/40 text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm"
            title="Enquadrar a Rota Completa no Mapa"
          >
            <MapTrifold size={16} className="text-cyan-400" />
            <span>Ver Rota Completa</span>
          </button>

          <button
            onClick={onTogglePlay}
            className={`px-4 py-2 rounded-xl font-bold text-xs flex items-center gap-2 transition-all shadow-lg ${
              isPlaying
                ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/20'
                : 'bg-sky-500 hover:bg-sky-400 text-white shadow-sky-500/30'
            }`}
          >
            {isPlaying ? <Pause size={16} weight="fill" /> : <Play size={16} weight="fill" />}
            <span>{isPlaying ? 'Pausar' : 'Refazer Caminho (Replay)'}</span>
          </button>

          <button
            onClick={onRestart}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all"
            title="Reiniciar do Início"
          >
            <ArrowClockwise size={16} />
          </button>

          <button
            onClick={onToggleFollow}
            className={`px-3 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all ${
              followVehicle
                ? 'bg-sky-500/15 border-sky-500/40 text-sky-300'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title="Seguir Câmera no Veículo"
          >
            <Crosshair size={16} className={followVehicle ? 'animate-pulse text-sky-400' : ''} />
            <span>Seguir Câmera</span>
          </button>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
          <Clock size={15} className="text-slate-400" />
          <span className="text-xs text-slate-400 font-medium">Velocidade:</span>
          <select
            value={speed}
            onChange={(e) => onSpeedChange(Number(e.target.value))}
            className="bg-slate-800 border border-slate-700 text-xs text-white rounded-lg px-2 py-1 font-mono font-bold focus:outline-none focus:border-sky-500 cursor-pointer"
          >
            <option value={1}>1x</option>
            <option value={2}>2x</option>
            <option value={5}>5x</option>
            <option value={10}>10x</option>
            <option value={20}>20x</option>
            <option value={50}>50x</option>
          </select>
        </div>
      </div>
    </div>
  );
}
