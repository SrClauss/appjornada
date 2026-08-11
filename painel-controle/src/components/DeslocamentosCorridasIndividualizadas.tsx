import React, { useState } from 'react';
import { Jornada, CorridaParticular, ComprovanteProcessado } from '../lib/types';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { MapPin, Navigation, Clock, Car, CurrencyDollar, Eye, CheckCircle2 } from 'lucide-react';

export interface CorridaIndividual {
  id: string;
  tipo: 'UBER' | '99' | 'PARTICULAR' | 'OUTROS';
  plataformaNome: string;
  origem?: string;
  destino?: string;
  origemCoords?: [number, number]; // [lat, lon]
  destinoCoords?: [number, number]; // [lat, lon]
  horarioInicio?: string;
  horarioFim?: string;
  distanciaKm?: number;
  duracaoMinutos?: number;
  valor: number;
  urlComprovante?: string;
}

interface DeslocamentosCorridasIndividualizadasProps {
  jornada: Jornada;
  selectedCorridaId?: string | null;
  onSelectCorrida: (corrida: CorridaIndividual | null) => void;
}

const formatCurrency = (val?: number) => {
  if (val === undefined || val === null || isNaN(val)) return 'R$ 0,00';
  return `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const DeslocamentosCorridasIndividualizadas: React.FC<DeslocamentosCorridasIndividualizadasProps> = ({
  jornada,
  selectedCorridaId,
  onSelectCorrida,
}) => {
  // Extrai todas as corridas individuais combinando corridas_particulares e comprovantes_processados
  const corridas: CorridaIndividual[] = [];

  // 1. Corridas Particulares
  if (jornada.corridas_particulares && jornada.corridas_particulares.length > 0) {
    jornada.corridas_particulares.forEach((cp: CorridaParticular, index) => {
      const origLat = cp.localizacao_inicio?.lat;
      const origLon = cp.localizacao_inicio?.lon;
      const destLat = cp.localizacao_fim?.lat;
      const destLon = cp.localizacao_fim?.lon;

      corridas.push({
        id: cp.id || `cp_${index}`,
        tipo: 'PARTICULAR',
        plataformaNome: 'Corrida Particular',
        origem: cp.localizacao_inicio ? `Lat: ${origLat?.toFixed(4)}, Lon: ${origLon?.toFixed(4)}` : 'Origem Registrada',
        destino: cp.localizacao_fim ? `Lat: ${destLat?.toFixed(4)}, Lon: ${destLon?.toFixed(4)}` : (cp.status === 'FINALIZADA' ? 'Destino Finalizado' : 'Em andamento'),
        origemCoords: origLat && origLon ? [origLat, origLon] : undefined,
        destinoCoords: destLat && destLon ? [destLat, destLon] : undefined,
        horarioInicio: cp.horario_inicio,
        horarioFim: cp.horario_fim,
        distanciaKm: cp.km_rodados ?? (cp.km_fim && cp.km_inicio ? Math.max(0, cp.km_fim - cp.km_inicio) : undefined),
        duracaoMinutos: cp.duracao_segundos ? Math.round(cp.duracao_segundos / 60) : undefined,
        valor: cp.valor_calculado ?? 0,
      });
    });
  }

  // 2. Comprovantes processados (Uber / 99 / Outros)
  const compList = jornada.faturamento?.comprovantes_processados || [];
  compList.forEach((comp: ComprovanteProcessado, index) => {
    const plat = (comp.plataforma || '').toLowerCase();
    let tipo: 'UBER' | '99' | 'OUTROS' = 'OUTROS';
    if (plat.includes('uber')) tipo = 'UBER';
    else if (plat.includes('99')) tipo = '99';

    corridas.push({
      id: `comp_${index}_${comp.plataforma}`,
      tipo,
      plataformaNome: comp.plataforma || 'Plataforma',
      origem: comp.origem || 'Extrato Lido',
      destino: comp.destino || 'Destino Lido',
      horarioInicio: comp.horario || comp.data_hora || (comp.data_processamento ? new Date(comp.data_processamento).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : undefined),
      valor: comp.valor || 0,
      urlComprovante: comp.url_comprovante,
    });
  });

  if (corridas.length === 0) {
    return (
      <Card className="p-4 border border-slate-100 shadow-sm rounded-xl text-center bg-slate-50/50 my-4">
        <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
          <Car size={16} className="text-slate-400" />
          Nenhum deslocamento de corrida individual registrado nesta jornada até o momento.
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-4 border border-slate-100 shadow-md rounded-2xl bg-card space-y-4 my-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
            <Navigation size={20} className="transform rotate-45" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">Deslocamentos de Corridas Individualizadas</h3>
            <p className="text-xs text-slate-500">Selecione uma corrida para isolar o trajeto e visualizar a rota no mapa</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedCorridaId && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onSelectCorrida(null)}
              className="text-xs text-slate-600 border-slate-200 hover:bg-slate-100"
            >
              Ver Todas no Mapa
            </Button>
          )}
          <Badge variant="outline" className="text-xs font-semibold border-indigo-200 text-indigo-700 bg-indigo-50/50">
            {corridas.length} corrida{corridas.length > 1 ? 's' : ''} individualizada{corridas.length > 1 ? 's' : ''}
          </Badge>
        </div>
      </div>

      {/* Grid de Lista de Corridas */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {corridas.map((c) => {
          const isSelected = selectedCorridaId === c.id;

          const getBadgeClass = (tipo: CorridaIndividual['tipo']) => {
            switch (tipo) {
              case 'UBER':
                return 'bg-slate-900 text-white';
              case '99':
                return 'bg-amber-500 text-slate-950 font-black';
              case 'PARTICULAR':
                return 'bg-emerald-600 text-white font-bold';
              default:
                return 'bg-indigo-600 text-white';
            }
          };

          return (
            <div
              key={c.id}
              onClick={() => onSelectCorrida(isSelected ? null : c)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer relative flex flex-col justify-between gap-3 ${
                isSelected
                  ? 'border-indigo-500 bg-indigo-50/40 shadow-md ring-2 ring-indigo-500/20'
                  : 'border-slate-100 hover:border-indigo-200 bg-white hover:bg-slate-50/60 shadow-sm'
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase font-bold tracking-wide ${getBadgeClass(c.tipo)}`}>
                    {c.plataformaNome}
                  </span>
                  <span className="text-sm font-black font-mono text-slate-900">
                    {formatCurrency(c.valor)}
                  </span>
                </div>

                <div className="space-y-1 text-xs text-slate-600">
                  <div className="flex items-start gap-1.5">
                    <MapPin size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                    <span className="truncate font-medium text-slate-700" title={c.origem}>
                      {c.origem || 'Origem não informada'}
                    </span>
                  </div>

                  <div className="flex items-start gap-1.5">
                    <MapPin size={14} className="text-rose-500 shrink-0 mt-0.5" />
                    <span className="truncate text-slate-500" title={c.destino}>
                      {c.destino || 'Destino não informado'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <div className="flex items-center gap-3">
                  {c.horarioInicio && (
                    <span className="flex items-center gap-1 font-medium text-slate-500">
                      <Clock size={12} className="text-slate-400" />
                      {c.horarioInicio}
                    </span>
                  )}
                  {c.distanciaKm !== undefined && c.distanciaKm > 0 && (
                    <span className="font-semibold text-indigo-600">
                      {c.distanciaKm.toFixed(1)} km
                    </span>
                  )}
                  {c.duracaoMinutos !== undefined && c.duracaoMinutos > 0 && (
                    <span className="text-slate-500">
                      {c.duracaoMinutos} min
                    </span>
                  )}
                </div>

                <span className={`inline-flex items-center gap-1 font-bold text-xs ${isSelected ? 'text-indigo-600' : 'text-slate-500 hover:text-indigo-600'}`}>
                  {isSelected ? (
                    <>
                      <CheckCircle2 size={14} className="text-indigo-600" />
                      Focado
                    </>
                  ) : (
                    <>
                      <Eye size={14} />
                      Ver no Mapa
                    </>
                  )}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
