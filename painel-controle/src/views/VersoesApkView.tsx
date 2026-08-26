import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  DownloadSimple, 
  DeviceMobile, 
  Sparkle, 
  MagnifyingGlass, 
  CheckCircle, 
  Wrench, 
  PaintBrush, 
  Bug, 
  Calendar, 
  HardDrive, 
  Clock, 
  ArrowClockwise,
  Check
} from '@phosphor-icons/react';
import api from '@/lib/api';

export interface Alteracao {
  tipo: 'FEATURE' | 'DESIGN' | 'MELHORIA' | 'FIX' | string;
  descricao: string;
}

export interface VersaoApk {
  versao: string;
  nome_versao: string;
  build_number: number;
  data_release: string;
  tamanho_mb: string;
  is_latest: boolean;
  url_download: string;
  url_download_direto: string;
  resumo: string;
  alteracoes: Alteracao[];
}

export function VersoesApkView() {
  const [versoes, setVersoes] = useState<VersaoApk[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState<string>('TODOS');

  const carregarVersoes = async () => {
    setLoading(true);
    try {
      const res = await api.get('/config/versao-app/historico');
      if (res.data?.versoes) {
        setVersoes(res.data.versoes);
      }
    } catch (err) {
      console.error('Erro ao carregar histórico de versões do APK:', err);
      // Fallback em caso de offline/carregamento inicial
      setVersoes([
        {
          versao: '1.1.0+13',
          nome_versao: '1.1.0',
          build_number: 13,
          data_release: '2026-08-26',
          tamanho_mb: '34.5 MB',
          is_latest: true,
          url_download: '/app-jornada-v1.1.0.apk',
          url_download_direto: '/app-release.apk',
          resumo: 'Atualização principal com Novo Painel de Ticket Médio, Design Fluent 2 e Mapa de Calor.',
          alteracoes: [
            { tipo: 'FEATURE', descricao: 'Implementado Mapa de Calor em tempo real para análises de rotas e tickets.' },
            { tipo: 'FEATURE', descricao: 'Integrado cálculo dinâmico de Ticket Médio e bônus em Metas & Performance.' },
            { tipo: 'DESIGN', descricao: 'Renovação visual completa com tokens Fluent Design 2 e componentes responsivos.' },
            { tipo: 'MELHORIA', descricao: 'Adicionado suporte a leitura rápida de QR Code para vinculo automático de motoristas.' },
            { tipo: 'MELHORIA', descricao: 'Tolerância ajustada para auditoria de paradas e abastecimentos.' },
            { tipo: 'FIX', descricao: 'Correção no sincronismo de dados em segundo plano quando sem sinal 4G.' }
          ]
        },
        {
          versao: '1.0.8+10',
          nome_versao: '1.0.8',
          build_number: 10,
          data_release: '2026-08-15',
          tamanho_mb: '32.1 MB',
          is_latest: false,
          url_download: '/app-jornada-v1.0.8.apk',
          url_download_direto: '/app-jornada-v1.0.8.apk',
          resumo: 'Módulo de Abastecimentos e Monitoramento de Jornada em Tempo Real.',
          alteracoes: [
            { tipo: 'FEATURE', descricao: 'Lançamento da tela de registro de abastecimentos com foto do comprovante.' },
            { tipo: 'MELHORIA', descricao: 'Otimização no consumo de bateria durante o rastreamento GPS contínuo.' },
            { tipo: 'FIX', descricao: 'Ajuste na reconexão automática do WebSocket de status.' }
          ]
        },
        {
          versao: '1.0.4+5',
          nome_versao: '1.0.4',
          build_number: 5,
          data_release: '2026-08-01',
          tamanho_mb: '30.8 MB',
          is_latest: false,
          url_download: '/app-jornada-v1.0.4.apk',
          url_download_direto: '/app-jornada-v1.0.4.apk',
          resumo: 'Versão Inicial Estável do aplicativo Motorista.',
          alteracoes: [
            { tipo: 'FEATURE', descricao: 'Início de jornada, paradas, fim de jornada e visualização de extrato.' },
            { tipo: 'FEATURE', descricao: 'Autenticação segura via JWT com suporte a perfis de motoristas.' }
          ]
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregarVersoes();
  }, []);

  const latestVersao = versoes.find((v) => v.is_latest) || versoes[0];

  const getTipoBadge = (tipo: string) => {
    switch (tipo.toUpperCase()) {
      case 'FEATURE':
        return (
          <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 gap-1">
            <Sparkle size={12} className="text-emerald-400" />
            Nova Funcionalidade
          </Badge>
        );
      case 'DESIGN':
        return (
          <Badge className="bg-purple-500/15 text-purple-300 border-purple-500/30 gap-1">
            <PaintBrush size={12} className="text-purple-400" />
            Interface & Design
          </Badge>
        );
      case 'MELHORIA':
        return (
          <Badge className="bg-cyan-500/15 text-cyan-300 border-cyan-500/30 gap-1">
            <Wrench size={12} className="text-cyan-400" />
            Melhoria
          </Badge>
        );
      case 'FIX':
        return (
          <Badge className="bg-amber-500/15 text-amber-300 border-amber-500/30 gap-1">
            <Bug size={12} className="text-amber-400" />
            Correção
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-slate-400">
            {tipo}
          </Badge>
        );
    }
  };

  const filteredVersoes = versoes.filter((v) => {
    const matchesSearch =
      v.versao.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.resumo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.alteracoes.some((a) => a.descricao.toLowerCase().includes(searchTerm.toLowerCase()));

    if (tipoFiltro === 'TODOS') return matchesSearch;
    return matchesSearch && v.alteracoes.some((a) => a.tipo.toUpperCase() === tipoFiltro);
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header com Título e Atualização */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 shadow-md">
              <DeviceMobile size={28} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Histórico & Alterações do APK
              </h1>
              <p className="text-sm text-slate-400">
                Acompanhe os lançamentos, novidades e faça o download direto das versões do App Motorista.
              </p>
            </div>
          </div>
        </div>

        <Button
          onClick={carregarVersoes}
          variant="outline"
          className="border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-300 gap-2 self-start md:self-auto"
        >
          <ArrowClockwise size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar Lista
        </Button>
      </div>

      {/* Destaque da Última Versão */}
      {latestVersao && !loading && (
        <Card className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-900 to-teal-950/60 border-teal-500/30 p-6 md:p-8 shadow-2xl">
          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <DeviceMobile size={180} className="text-teal-400" />
          </div>

          <div className="relative z-10 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-teal-500/20 text-teal-300 border border-teal-500/40 uppercase tracking-wider flex items-center gap-1.5 shadow-sm">
                <CheckCircle size={14} className="text-teal-400" />
                Versão Mais Recente (Produção)
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Calendar size={14} className="text-slate-500" />
                Lançado em {latestVersao.data_release}
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <HardDrive size={14} className="text-slate-500" />
                {latestVersao.tamanho_mb}
              </span>
            </div>

            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pt-2">
              <div className="space-y-1">
                <h2 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                  App Motorista v{latestVersao.nome_versao}
                  <span className="text-sm font-semibold font-mono text-teal-400 bg-teal-950/80 border border-teal-800/60 px-2.5 py-0.5 rounded-md">
                    Build #{latestVersao.build_number}
                  </span>
                </h2>
                <p className="text-base text-slate-300 max-w-2xl leading-relaxed">
                  {latestVersao.resumo}
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 flex-shrink-0">
                <a
                  href={latestVersao.url_download_direto}
                  download={`app-jornada-v${latestVersao.nome_versao}.apk`}
                >
                  <Button className="w-full sm:w-auto bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold px-6 py-6 rounded-xl shadow-lg shadow-emerald-950/50 transition-all gap-2 text-base">
                    <DownloadSimple size={22} className="animate-bounce" />
                    Baixar APK v{latestVersao.nome_versao}
                  </Button>
                </a>
              </div>
            </div>

            {/* Destaques das alterações da última versão */}
            <div className="pt-4 border-t border-slate-800/80">
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                Principais Novidades desta Release:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {latestVersao.alteracoes.map((alt, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/60 text-xs text-slate-200"
                  >
                    <div className="mt-0.5">{getTipoBadge(alt.tipo)}</div>
                    <span className="leading-snug">{alt.descricao}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Filtros e Busca */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
        <div className="relative w-full sm:w-80">
          <MagnifyingGlass size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <Input
            placeholder="Buscar por versão ou funcionalidade..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9 bg-slate-900 border-slate-800 text-slate-200 placeholder:text-slate-500"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {['TODOS', 'FEATURE', 'DESIGN', 'MELHORIA', 'FIX'].map((cat) => (
            <button
              key={cat}
              onClick={() => setTipoFiltro(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                tipoFiltro === cat
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/40'
                  : 'bg-slate-900 text-slate-400 border border-slate-800 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {cat === 'TODOS' ? 'Todas Alterações' : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Timeline de Histórico de Versões */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
          <Clock size={20} className="text-teal-400" />
          Linha do Tempo de Lançamentos
        </h3>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-36 w-full rounded-2xl bg-slate-900" />
            <Skeleton className="h-36 w-full rounded-2xl bg-slate-900" />
          </div>
        ) : filteredVersoes.length === 0 ? (
          <Card className="bg-slate-950/60 border-slate-800 p-8 text-center">
            <p className="text-slate-400">Nenhuma versão encontrada para o filtro pesquisado.</p>
          </Card>
        ) : (
          <div className="relative border-l-2 border-slate-800 ml-4 md:ml-6 space-y-8 pl-6 md:pl-8">
            {filteredVersoes.map((item) => (
              <div key={item.versao} className="relative group">
                {/* Indicador visual na linha do tempo */}
                <div
                  className={`absolute -left-[31px] md:-left-[39px] top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                    item.is_latest
                      ? 'bg-teal-500 border-teal-300 shadow-md shadow-teal-500/50'
                      : 'bg-slate-900 border-slate-700 group-hover:border-teal-500'
                  }`}
                >
                  {item.is_latest && <Check size={12} className="text-slate-950 font-bold" />}
                </div>

                <Card className="bg-slate-950/80 border-slate-800 hover:border-slate-700 p-5 md:p-6 transition-all space-y-4 shadow-xl">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h4 className="text-xl font-bold text-white flex items-center gap-2">
                        v{item.nome_versao}
                        {item.is_latest && (
                          <Badge className="bg-teal-500/15 text-teal-300 border-teal-500/30 text-[10px]">
                            Atual
                          </Badge>
                        )}
                      </h4>
                      <span className="text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">
                        Build #{item.build_number}
                      </span>
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Calendar size={13} />
                        {item.data_release}
                      </span>
                      <span className="text-xs text-slate-500 flex items-center gap-1">
                        <HardDrive size={13} />
                        {item.tamanho_mb}
                      </span>
                    </div>

                    <a href={item.url_download_direto} download={`app-jornada-v${item.nome_versao}.apk`}>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 font-semibold gap-1.5 text-xs"
                      >
                        <DownloadSimple size={15} />
                        Baixar (v{item.nome_versao})
                      </Button>
                    </a>
                  </div>

                  <p className="text-sm text-slate-300 font-medium">{item.resumo}</p>

                  <div className="space-y-2 pt-1">
                    <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      Lista de Alterações:
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {item.alteracoes.map((alt, idx) => (
                        <div
                          key={idx}
                          className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-900/60 border border-slate-800/40 text-xs text-slate-300"
                        >
                          <div className="mt-0.5">{getTipoBadge(alt.tipo)}</div>
                          <span className="leading-snug">{alt.descricao}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
