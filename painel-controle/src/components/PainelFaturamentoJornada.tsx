import React from 'react';
import { Jornada } from '../lib/types';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { CurrencyDollar, Car, FileText, ArrowUpRight } from '@phosphor-icons/react';
import api from '../lib/api';

interface PainelFaturamentoJornadaProps {
  jornada: Jornada;
}

const formatCurrency = (val?: number) => {
  if (val === undefined || val === null || isNaN(val)) return 'R$ 0,00';
  return `R$ ${val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const PainelFaturamentoJornada: React.FC<PainelFaturamentoJornadaProps> = ({ jornada }) => {
  const fat = jornada.faturamento || {};
  const uberVal = fat.uber ?? 0;
  const noventaNoveVal = fat.noventa_nove ?? 0;
  const outrosVal = fat.outros ?? 0;
  const totalDia = fat.total_dia ?? (uberVal + noventaNoveVal + outrosVal);

  const uberCorridas = fat.corridas_uber ?? 0;
  const noventaNoveCorridas = fat.corridas_99 ?? 0;
  const outrosCorridas = fat.corridas_outros ?? (jornada.corridas_particulares?.length ?? 0);
  const totalCorridas = uberCorridas + noventaNoveCorridas + outrosCorridas;

  // Cálculos de porcentagem para a barra de distribuição
  const safeTotal = totalDia > 0 ? totalDia : 1;
  const pctUber = Math.round((uberVal / safeTotal) * 100);
  const pct99 = Math.round((noventaNoveVal / safeTotal) * 100);
  const pctOutros = Math.max(0, 100 - pctUber - pct99);

  const getMediaUrl = (url?: string) => {
    if (!url) return '';
    if (url.startsWith('http')) return url;
    const base = api.defaults.baseURL?.replace('/api', '') || '';
    return `${base}${url}`;
  };

  return (
    <div className="space-y-4 my-4">
      {/* Header do Painel */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
            <CurrencyDollar size={22} weight="bold" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-800">Painel de Faturamento por Plataforma</h3>
            <p className="text-xs text-slate-500">Divisão de receita Uber, 99, Corridas Particulares e Total da Jornada</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-sm px-3 py-1">
            Total: {formatCurrency(totalDia)}
          </Badge>
          {totalCorridas > 0 && (
            <Badge variant="outline" className="text-slate-600 border-slate-200 text-xs">
              {totalCorridas} corrida{totalCorridas > 1 ? 's' : ''} no total
            </Badge>
          )}
        </div>
      </div>

      {/* Grid de Cards por Plataforma */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* UBER CARD */}
        <Card className="p-4 border border-slate-800/10 shadow-sm bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black tracking-wider uppercase text-slate-300 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
              Uber
            </span>
            {fat.comprovante_uber_url && (
              <a
                href={getMediaUrl(fat.comprovante_uber_url)}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] bg-white/10 hover:bg-white/20 text-white px-2 py-0.5 rounded-full flex items-center gap-1 transition-colors"
                title="Ver Comprovante Uber"
              >
                Comprovante <ArrowUpRight size={10} />
              </a>
            )}
          </div>
          <div className="mt-1">
            <h4 className="text-2xl font-black font-mono tracking-tight">{formatCurrency(uberVal)}</h4>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <Car size={14} className="text-slate-300" />
              {uberCorridas} corrida{uberCorridas !== 1 ? 's' : ''} declarada{uberCorridas !== 1 ? 's' : ''}
            </p>
          </div>
        </Card>

        {/* 99 CARD */}
        <Card className="p-4 border border-amber-400/30 shadow-sm bg-gradient-to-br from-amber-500 to-amber-600 text-slate-950 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black tracking-wider uppercase text-slate-900 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-900"></span>
              99 Tecnologia
            </span>
            {fat.comprovante_99_url && (
              <a
                href={getMediaUrl(fat.comprovante_99_url)}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] bg-slate-950/20 hover:bg-slate-950/30 text-slate-950 font-bold px-2 py-0.5 rounded-full flex items-center gap-1 transition-colors"
                title="Ver Comprovante 99"
              >
                Comprovante <ArrowUpRight size={10} />
              </a>
            )}
          </div>
          <div className="mt-1">
            <h4 className="text-2xl font-black font-mono tracking-tight text-slate-950">{formatCurrency(noventaNoveVal)}</h4>
            <p className="text-xs text-slate-900/80 mt-1 font-medium flex items-center gap-1">
              <Car size={14} className="text-slate-900" />
              {noventaNoveCorridas} corrida{noventaNoveCorridas !== 1 ? 's' : ''} declarada{noventaNoveCorridas !== 1 ? 's' : ''}
            </p>
          </div>
        </Card>

        {/* PARTICULARES / OUTROS CARD */}
        <Card className="p-4 border border-emerald-200 shadow-sm bg-gradient-to-br from-emerald-50 to-teal-50 text-slate-800 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black tracking-wider uppercase text-emerald-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Particulares / Outros
            </span>
            {fat.comprovante_outros_url && (
              <a
                href={getMediaUrl(fat.comprovante_outros_url)}
                target="_blank"
                rel="noreferrer"
                className="text-[10px] bg-emerald-200/60 hover:bg-emerald-200 text-emerald-900 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 transition-colors"
              >
                Comprovante <ArrowUpRight size={10} />
              </a>
            )}
          </div>
          <div className="mt-1">
            <h4 className="text-2xl font-black font-mono tracking-tight text-emerald-700">{formatCurrency(outrosVal)}</h4>
            <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
              <Car size={14} className="text-emerald-600" />
              {outrosCorridas} corrida{outrosCorridas !== 1 ? 's' : ''} registrada{outrosCorridas !== 1 ? 's' : ''}
            </p>
          </div>
        </Card>

        {/* TOTAL CONSOLIDADO CARD */}
        <Card className="p-4 border border-indigo-200 shadow-sm bg-gradient-to-br from-indigo-50 to-slate-50 text-slate-800 rounded-xl relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-black tracking-wider uppercase text-indigo-800 flex items-center gap-1.5">
              <CurrencyDollar size={14} className="text-indigo-600" />
              Total Bruto Dia
            </span>
          </div>
          <div className="mt-1">
            <h4 className="text-2xl font-black font-mono tracking-tight text-indigo-900">{formatCurrency(totalDia)}</h4>
            <p className="text-xs text-indigo-600 font-semibold mt-1">
              100% faturamento consolidado
            </p>
          </div>
        </Card>
      </div>

      {/* Barra de Distribuição Percentual */}
      {totalDia > 0 && (
        <Card className="p-4 border border-slate-100 shadow-sm rounded-xl space-y-2 bg-card">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
            <span>Distribuição Percentual da Receita</span>
            <div className="flex items-center gap-4 text-[11px]">
              <span className="flex items-center gap-1 text-slate-800">
                <span className="w-2.5 h-2.5 rounded-sm bg-slate-900 inline-block"></span> Uber ({pctUber}%)
              </span>
              <span className="flex items-center gap-1 text-amber-600">
                <span className="w-2.5 h-2.5 rounded-sm bg-amber-500 inline-block"></span> 99 ({pct99}%)
              </span>
              <span className="flex items-center gap-1 text-emerald-600">
                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block"></span> Particulares ({pctOutros}%)
              </span>
            </div>
          </div>
          <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden flex">
            {pctUber > 0 && (
              <div
                style={{ width: `${pctUber}%` }}
                className="bg-slate-900 h-full transition-all duration-500"
                title={`Uber: ${formatCurrency(uberVal)} (${pctUber}%)`}
              />
            )}
            {pct99 > 0 && (
              <div
                style={{ width: `${pct99}%` }}
                className="bg-amber-500 h-full transition-all duration-500"
                title={`99: ${formatCurrency(noventaNoveVal)} (${pct99}%)`}
              />
            )}
            {pctOutros > 0 && (
              <div
                style={{ width: `${pctOutros}%` }}
                className="bg-emerald-500 h-full transition-all duration-500"
                title={`Particulares/Outros: ${formatCurrency(outrosVal)} (${pctOutros}%)`}
              />
            )}
          </div>
        </Card>
      )}

      {/* Tabela de Comprovantes / Extratos Lidos via IA (comprovantes_processados) */}
      {fat.comprovantes_processados && fat.comprovantes_processados.length > 0 && (
        <Card className="p-4 border border-slate-100 shadow-sm rounded-xl space-y-3 bg-card">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
            <FileText size={16} className="text-slate-500" />
            Comprovantes e Recibos Lidos via OCR/IA ({fat.comprovantes_processados.length})
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-slate-600">
              <thead className="text-[11px] font-bold text-slate-500 uppercase bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="py-2 px-3">Plataforma</th>
                  <th className="py-2 px-3">Valor Extraído</th>
                  <th className="py-2 px-3">Origem / Destino</th>
                  <th className="py-2 px-3">Data / Hora</th>
                  <th className="py-2 px-3 text-right">Mídia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {fat.comprovantes_processados.map((comp, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2.5 px-3 font-semibold">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        comp.plataforma?.toLowerCase().includes('uber')
                          ? 'bg-slate-900 text-white'
                          : comp.plataforma?.toLowerCase().includes('99')
                          ? 'bg-amber-500 text-slate-950'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}>
                        {comp.plataforma || 'N/I'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-900">
                      {formatCurrency(comp.valor)}
                    </td>
                    <td className="py-2.5 px-3 max-w-xs truncate text-slate-500">
                      {comp.origem || comp.destino ? `${comp.origem || '—'} ➔ ${comp.destino || '—'}` : 'N/A'}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-700">
                      {comp.horario || comp.data_hora || (comp.data_processamento ? new Date(comp.data_processamento).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }) : '—')}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      {comp.url_comprovante ? (
                        <a
                          href={getMediaUrl(comp.url_comprovante)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-sky-600 hover:text-sky-800 font-semibold"
                        >
                          Ver Print <ArrowUpRight size={12} />
                        </a>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
