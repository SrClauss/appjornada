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
  is_latest: bool;
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
      setVersoes([
        {
          versao: '1.2.4+17',
          nome_versao: '1.2.4',
          build_number: 17,
          data_release: '2026-09-03',
          tamanho_mb: '54.6 MB',
          is_latest: true,
          url_download: '/config/apk/download',
          url_download_direto: '/config/apk/download',
          resumo: 'Versão de produção gerenciada dinamicamente no MinIO e MongoDB.',
          alteracoes: [
            { tipo: 'FEATURE', descricao: 'Armazenamento dinâmico do APK no MinIO com controle de versão no MongoDB.' },
            { tipo: 'FIX', descricao: 'Correção no roteamento de sessões de auditoria do app motorista.' }
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

  const resolveDownloadUrl = (url?: string) => {
    if (!url) return `${api.defaults.baseURL || ''}/config/apk/download`;
    if (url.startsWith('http')) return url;
    return `${api.defaults.baseURL || ''}${url.startsWith('/') ? '' : '/'}${url}`;
  };

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
      v.nome_versao.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.resumo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.alteracoes.some((a) => a.descricao.toLowerCase().includes(searchTerm.toLowerCase()));

    if (tipoFiltro === 'TODOS') return matchesSearch;
    return matchesSearch && v.alteracoes.some((a) => a.tipo.toUpperCase() === tipoFiltro);
  });

  return (
    <div className="space-y-6 pb-12">
      {/* Header Principal */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-teal-400 uppercase tracking-wider mb-1">
            <DeviceMobile size={16} />
            <span>Distribuição de Aplicativos</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Versões & Alterações do App Motorista (APK)
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Histórico completo de releases do aplicativo Android mantido no MinIO e MongoDB.
          </p>
        </div>

        <Button
          onClick={carregarVersoes}
          variant="outline"
          className="border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-200 gap-2 self-start md:self-auto rounded-xl"
        >
          <ArrowClockwise size={16} className={loading ? 'animate-spin' : ''} />
          Atualizar Lista
        </Button>
      </div>

      {/* Card da Última Versão (Destaque Principal) */}
      {latestVersao && (
        <Card className="bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 border-teal-500/30 shadow-xl overflow-hidden relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/5 rounded-full blur-3xl pointer-events-none" />

          <div className="p-6 md:p-8 space-y-6 relative z-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 mb-2">
                  <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-xs px-2.5 py-0.5 font-bold uppercase tracking-wider flex items-center gap-1">
                    <Sparkle size={12} weight="fill" />
                    Versão Atual Ativa (MinIO & DB)
                  </Badge>
                </div>
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
                  href={resolveDownloadUrl(latestVersao.url_download_direto || latestVersao.url_download)}
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
                    className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition-colors"
                  >
                    <div className="mt-0.5 shrink-0">{getTipoBadge(alt.tipo)}</div>
                    <p className="text-xs text-slate-300 font-medium leading-normal">{alt.descricao}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Seção do Histórico Completo */}
      <div className="space-y-4 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">
              Histórico de Versões Anteriores
            </h3>
            <p className="text-xs text-slate-400">
              Changelog completo das releases do aplicativo mobile.
            </p>
          </div>

          <div className="relative w-full sm:w-72">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <Input
              type="text"
              placeholder="Buscar por versão ou resumo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 bg-slate-900 border-slate-800 text-xs text-slate-200 rounded-xl focus:ring-teal-500/30"
            />
          </div>
        </div>

        {filteredVersoes.length === 0 ? (
          <Card className="bg-slate-900/40 border-slate-800/80 p-8 text-center">
            <p className="text-sm text-slate-400">Nenhuma versão encontrada para o termo pesquisado.</p>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredVersoes.map((item, idx) => (
              <Card
                key={idx}
                className={`border bg-slate-900/60 transition-all ${
                  item.is_latest
                    ? 'border-teal-500/40 shadow-md shadow-teal-950/20'
                    : 'border-slate-800/80 hover:border-slate-700/80'
                }`}
              >
                <div className="p-5 md:p-6 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <h4 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                        v{item.nome_versao}
                        {item.is_latest && (
                          <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-[10px] uppercase font-bold">
                            Ativa no MinIO
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

                    <a href={resolveDownloadUrl(item.url_download_direto || item.url_download)} download={`app-jornada-v${item.nome_versao}.apk`}>
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
                      Alterações nesta versão:
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {item.alteracoes.map((alt, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-slate-400 bg-slate-950/40 p-2 rounded-lg border border-slate-900">
                          <div className="mt-0.5 shrink-0">{getTipoBadge(alt.tipo)}</div>
                          <span className="text-slate-300">{alt.descricao}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
