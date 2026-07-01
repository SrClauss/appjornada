import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Trash, 
  Image, 
  FolderSimple, 
  MagnifyingGlass, 
  DownloadSimple, 
  Clock, 
  Info,
  Calendar,
  FilePdf
} from '@phosphor-icons/react';
import api from '@/lib/api';

interface UploadedMedia {
  url: string;
  filename: string;
  contexto: string;
  tamanho_bytes: number;
  data_criacao: string | null;
}

const CONTEXTO_LABELS: Record<string, string> = {
  km_inicial: 'Odômetro Inicial',
  km_final: 'Odômetro Final',
  cnh: 'CNH Motorista',
  clrv: 'CRLV Veículo',
  veiculo: 'Foto Veículo',
  comprovante: 'Faturamento',
  sinistro: 'Sinistro',
  nota_fiscal: 'Nota Fiscal',
  vistoria: 'Checklist / Vistoria',
  outros: 'Outros Documentos'
};

const CONTEXTO_COLORS: Record<string, string> = {
  km_inicial: 'bg-blue-50 text-blue-700 border-blue-100',
  km_final: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  cnh: 'bg-purple-50 text-purple-700 border-purple-100',
  clrv: 'bg-amber-50 text-amber-700 border-amber-100',
  veiculo: 'bg-teal-50 text-teal-700 border-teal-100',
  comprovante: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  sinistro: 'bg-rose-50 text-rose-700 border-rose-100',
  nota_fiscal: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  vistoria: 'bg-sky-50 text-sky-700 border-sky-100',
  outros: 'bg-slate-50 text-slate-700 border-slate-100'
};

export function MediaManagementView() {
  const [medias, setMedias] = useState<UploadedMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterContext, setFilterContext] = useState('all');

  const fetchMedias = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/uploads');
      setMedias(data);
    } catch (e) {
      console.error('Erro ao buscar mídias:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedias();
  }, []);

  const handleDelete = async (contexto: string, filename: string) => {
    if (!window.confirm('Tem certeza que deseja deletar este arquivo permanentemente? Esta ação não pode ser desfeita.')) {
      return;
    }
    try {
      await api.delete(`/uploads/${contexto}/${filename}`);
      setMedias((prev) => prev.filter((m) => !(m.contexto === contexto && m.filename === filename)));
    } catch (e) {
      console.error('Erro ao deletar mídia:', e);
      alert('Não foi possível excluir o arquivo.');
    }
  };

  // Filter list
  const filtered = medias.filter((m) => {
    const matchesSearch = m.filename.toLowerCase().includes(search.toLowerCase());
    const matchesContext = filterContext === 'all' || m.contexto === filterContext;
    return matchesSearch && matchesContext;
  });

  const totalSizeMB = (medias.reduce((acc, m) => acc + m.tamanho_bytes, 0) / (1024 * 1024)).toFixed(2);

  const getFullUrl = (url: string) => {
    if (url.startsWith('http')) return url;
    const base = api.defaults.baseURL?.replace('/api', '') || '';
    return `${base}${url}`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Image size={28} className="text-blue-600" />
            Gestão de Mídias Uploaded
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Visualize, filtre e gerencie todos os arquivos de vistoria, comprovantes e odômetros salvos no sistema.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchMedias} className="text-xs px-3">
          Atualizar Lista
        </Button>
      </div>

      {/* KPI Stats Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 flex items-center gap-4 bg-gradient-to-br from-blue-50/50 to-white shadow-sm border border-slate-100 rounded-2xl">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl">
            <FolderSimple size={24} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Total de Arquivos</p>
            <h4 className="text-xl font-bold text-slate-800 mt-0.5">{medias.length}</h4>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4 bg-gradient-to-br from-emerald-50/50 to-white shadow-sm border border-slate-100 rounded-2xl">
          <div className="p-3 bg-emerald-100 text-emerald-600 rounded-xl">
            <Info size={24} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Espaço Ocupado</p>
            <h4 className="text-xl font-bold text-slate-800 mt-0.5">{totalSizeMB} MB</h4>
          </div>
        </Card>
        <Card className="p-4 flex items-center gap-4 bg-gradient-to-br from-purple-50/50 to-white shadow-sm border border-slate-100 rounded-2xl">
          <div className="p-3 bg-purple-100 text-purple-600 rounded-xl">
            <Clock size={24} />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Filtrados / Exibidos</p>
            <h4 className="text-xl font-bold text-slate-800 mt-0.5">{filtered.length}</h4>
          </div>
        </Card>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-slate-50/50 p-4 rounded-2xl border border-slate-100">
        <div className="relative w-full sm:max-w-xs">
          <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <Input
            placeholder="Buscar por nome do arquivo..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 text-xs"
          />
        </div>
        <div className="flex gap-2 w-full sm:w-auto items-center">
          <span className="text-xs text-slate-500 whitespace-nowrap">Filtrar Categoria:</span>
          <select
            value={filterContext}
            onChange={(e) => setFilterContext(e.target.value)}
            className="text-xs bg-white border border-slate-200 rounded-lg p-2 focus:outline-none shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-full sm:w-auto min-w-[180px]"
          >
            <option value="all">Todas as Mídias</option>
            {Object.entries(CONTEXTO_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Media Grid */}
      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i} className="p-3 border border-slate-100 shadow-sm rounded-2xl space-y-3">
              <Skeleton className="h-40 w-full rounded-xl" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-4 border-dashed border-2 border-slate-200 max-w-2xl mx-auto mt-6">
          <div className="p-4 bg-slate-50 rounded-full">
            <Image size={36} className="text-slate-400" />
          </div>
          <div className="space-y-1">
            <div className="font-semibold text-slate-700 text-sm">Nenhum Arquivo Encontrado</div>
            <p className="text-xs text-slate-400 max-w-sm">
              Não existem mídias carregadas com os filtros selecionados no momento.
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {filtered.map((m, idx) => {
            const isPdf = m.filename.toLowerCase().endsWith('.pdf');
            const fileUrl = getFullUrl(m.url);
            
            return (
              <Card key={idx} className="p-3 border border-slate-150 shadow-md hover:shadow-lg rounded-2xl flex flex-col justify-between gap-3 bg-white transition-all duration-200 hover:-translate-y-0.5">
                <div className="space-y-2">
                  {/* Preview Container */}
                  <div className="w-full h-40 rounded-xl overflow-hidden border border-slate-100 bg-slate-50 flex items-center justify-center relative group">
                    {isPdf ? (
                      <div className="flex flex-col items-center gap-2 text-red-500">
                        <FilePdf size={44} weight="duotone" />
                        <span className="text-[10px] font-bold text-slate-500">Documento PDF</span>
                      </div>
                    ) : (
                      <img 
                        src={fileUrl} 
                        alt={m.filename} 
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200" 
                      />
                    )}
                    {/* Hover Overlay */}
                    <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <a 
                        href={fileUrl} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="p-2 bg-white text-slate-700 hover:bg-slate-100 rounded-full shadow-md transition-colors"
                        title="Visualizar tela inteira"
                      >
                        <FolderSimple size={16} />
                      </a>
                      <a 
                        href={fileUrl} 
                        download={m.filename}
                        className="p-2 bg-blue-600 text-white hover:bg-blue-700 rounded-full shadow-md transition-colors"
                        title="Baixar arquivo"
                      >
                        <DownloadSimple size={16} />
                      </a>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="space-y-1 px-1">
                    <Badge variant="outline" className={`text-[9px] font-bold uppercase ${CONTEXTO_COLORS[m.contexto] || 'bg-slate-100'}`}>
                      {CONTEXTO_LABELS[m.contexto] || m.contexto}
                    </Badge>
                    <div className="text-xs font-semibold text-slate-700 truncate" title={m.filename}>
                      {m.filename}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                      <span className="flex items-center gap-1">
                        <Calendar size={12} />
                        {m.data_criacao ? new Date(m.data_criacao).toLocaleDateString('pt-BR') : 'Sem data'}
                      </span>
                      <span className="font-mono">{formatBytes(m.tamanho_bytes)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100 mt-auto">
                  <a 
                    href={fileUrl} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="flex-1 text-center"
                  >
                    <Button variant="outline" size="sm" className="w-full text-[11px] h-8 px-2 py-1">
                      Visualizar
                    </Button>
                  </a>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => handleDelete(m.contexto, m.filename)}
                    className="text-red-500 hover:text-red-700 hover:bg-red-50 h-8 w-8 p-0"
                    title="Excluir arquivo permanentemente"
                  >
                    <Trash size={16} />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
