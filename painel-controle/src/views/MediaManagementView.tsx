import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { 
  Trash, 
  Image as ImageIcon, 
  FolderSimple, 
  MagnifyingGlass, 
  DownloadSimple, 
  Clock, 
  Info,
  Calendar,
  FilePdf,
  Lock,
  X,
  CaretLeft,
  CaretRight,
  Check,
  ArrowSquareOut
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
  sinistro: 'Sinistro / Avaria',
  nota_fiscal: 'Nota Fiscal',
  vistoria: 'Checklist / Vistoria',
  extrato_video: 'Vídeo Extrato IA',
  extrato_frames: 'Frames do Vídeo IA',
  hodometro: 'Foto Hodômetro',
  outros: 'Outros Documentos'
};

const CONTEXTO_COLORS: Record<string, string> = {
  km_inicial: 'bg-blue-50 text-blue-700 border-blue-100',
  km_final: 'bg-indigo-50 text-indigo-700 border-indigo-100',
  cnh: 'bg-purple-50 text-purple-700 border-purple-100',
  clrv: 'bg-pink-50 text-pink-700 border-pink-100',
  veiculo: 'bg-cyan-50 text-cyan-700 border-cyan-100',
  comprovante: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  sinistro: 'bg-red-50 text-red-700 border-red-100',
  nota_fiscal: 'bg-amber-50 text-amber-700 border-amber-100',
  vistoria: 'bg-orange-50 text-orange-700 border-orange-100',
  extrato_video: 'bg-violet-50 text-violet-700 border-violet-100',
  extrato_frames: 'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-100',
  hodometro: 'bg-sky-50 text-sky-700 border-sky-100',
};

const DELETABLE_CONTEXTS = [
  'km_inicial', 'km_final', 'vistoria', 'sinistro', 'comprovante', 
  'extrato_video', 'extrato_frames', 'hodometro', 'nota_fiscal', 'cnh', 'clrv', 'veiculo', 'outros'
];

export function MediaManagementView() {
  const [medias, setMedias] = useState<UploadedMedia[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Filtro rápido por categoria: 'all' | 'odometros' | 'vistoria' | 'sinistro' | 'comprovante' | 'protected'
  const [quickFilter, setQuickFilter] = useState<string>('all');
  
  // Itens selecionados para exclusão em lote
  const [selectedItems, setSelectedItems] = useState<UploadedMedia[]>([]);
  
  // Visualizador / Lightbox
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);

  const fetchMedias = async () => {
    try {
      setLoading(true);
      const { data } = await api.get('/uploads');
      setMedias(data);
      setSelectedItems([]);
    } catch (e) {
      console.error('Erro ao buscar mídias:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedias();
  }, []);

  const getFullUrl = (url: string) => {
    if (url.startsWith('http')) return url;
    const base = api.defaults.baseURL?.replace('/api', '') || '';
    return `${base}${url}`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Filtragem da lista
  const filtered = medias.filter((m) => {
    const matchesSearch = m.filename.toLowerCase().includes(search.toLowerCase());
    
    let matchesCategory = true;
    if (quickFilter === 'odometros') {
      matchesCategory = m.contexto === 'km_inicial' || m.contexto === 'km_final';
    } else if (quickFilter === 'vistoria') {
      matchesCategory = m.contexto === 'vistoria';
    } else if (quickFilter === 'sinistro') {
      matchesCategory = m.contexto === 'sinistro';
    } else if (quickFilter === 'comprovante') {
      matchesCategory = m.contexto === 'comprovante';
    } else if (quickFilter === 'protected') {
      matchesCategory = !DELETABLE_CONTEXTS.includes(m.contexto);
    } else if (quickFilter !== 'all') {
      matchesCategory = m.contexto === quickFilter;
    }
    
    return matchesSearch && matchesCategory;
  });

  const totalSizeMB = (medias.reduce((acc, m) => acc + m.tamanho_bytes, 0) / (1024 * 1024)).toFixed(1);

  // Seleção e exclusão individual
  const isSelected = (m: UploadedMedia) => {
    return selectedItems.some((item) => item.contexto === m.contexto && item.filename === m.filename);
  };

  const handleToggleSelect = (m: UploadedMedia, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!DELETABLE_CONTEXTS.includes(m.contexto)) return;

    setSelectedItems((prev) => {
      const exists = prev.some((item) => item.contexto === m.contexto && item.filename === m.filename);
      if (exists) {
        return prev.filter((item) => !(item.contexto === m.contexto && item.filename === m.filename));
      } else {
        return [...prev, m];
      }
    });
  };

  const handleSelectAllEligible = () => {
    const eligible = filtered.filter(m => DELETABLE_CONTEXTS.includes(m.contexto));
    const allSelected = eligible.every(m => isSelected(m));
    
    if (allSelected) {
      // Remove apenas os itens que estão visíveis e elegíveis
      setSelectedItems(prev => 
        prev.filter(p => !eligible.some(el => el.contexto === p.contexto && el.filename === p.filename))
      );
    } else {
      // Adiciona todos os visíveis elegíveis que ainda não estão selecionados
      setSelectedItems(prev => {
        const next = [...prev];
        eligible.forEach(el => {
          if (!next.some(n => n.contexto === el.contexto && n.filename === el.filename)) {
            next.push(el);
          }
        });
        return next;
      });
    }
  };

  const handleDeleteSingle = async (contexto: string, filename: string) => {
    if (!window.confirm('Tem certeza que deseja deletar este arquivo permanentemente?')) {
      return;
    }
    try {
      await api.delete(`/uploads/${contexto}/${filename}`);
      setMedias((prev) => prev.filter((m) => !(m.contexto === contexto && m.filename === filename)));
      setSelectedItems((prev) => prev.filter((m) => !(m.contexto === contexto && m.filename === filename)));
    } catch (e) {
      console.error('Erro ao deletar:', e);
      alert('Não foi possível excluir o arquivo.');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedItems.length === 0) return;
    const count = selectedItems.length;
    if (!window.confirm(`Confirma a exclusão permanente de ${count} mídias selecionadas?`)) {
      return;
    }
    try {
      const payload = {
        items: selectedItems.map(item => ({
          contexto: item.contexto,
          filename: item.filename
        }))
      };
      await api.post('/uploads/bulk-delete', payload);
      setMedias((prev) => 
        prev.filter(m => !selectedItems.some(sel => sel.contexto === m.contexto && sel.filename === m.filename))
      );
      setSelectedItems([]);
      alert(`${count} mídias excluídas.`);
    } catch (e) {
      console.error('Erro na exclusão em lote:', e);
      alert('Erro ao excluir as mídias selecionadas.');
    }
  };

  // Controle de Preview do Lightbox
  const handleOpenPreview = (m: UploadedMedia) => {
    const idx = filtered.findIndex((x) => x.contexto === m.contexto && x.filename === m.filename);
    if (idx !== -1) {
      setPreviewIndex(idx);
    }
  };

  const handlePrev = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (previewIndex === null || filtered.length === 0) return;
    setPreviewIndex((prev) => (prev! > 0 ? prev! - 1 : filtered.length - 1));
  };

  const handleNext = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (previewIndex === null || filtered.length === 0) return;
    setPreviewIndex((prev) => (prev! < filtered.length - 1 ? prev! + 1 : 0));
  };

  const handleDeleteFromPreview = async () => {
    if (previewIndex === null) return;
    const item = filtered[previewIndex];
    if (!window.confirm('Excluir este arquivo permanentemente?')) return;
    try {
      await api.delete(`/uploads/${item.contexto}/${item.filename}`);
      setMedias((prev) => prev.filter((m) => !(m.contexto === item.contexto && m.filename === item.filename)));
      setSelectedItems((prev) => prev.filter((m) => !(m.contexto === item.contexto && m.filename === item.filename)));
      
      if (filtered.length <= 1) {
        setPreviewIndex(null);
      } else {
        if (previewIndex >= filtered.length - 1) {
          setPreviewIndex(filtered.length - 2);
        }
      }
    } catch (e) {
      console.error(e);
      alert('Erro ao excluir.');
    }
  };

  // Preview item atual
  const previewItem = previewIndex !== null ? filtered[previewIndex] : null;

  return (
    <div className="space-y-5 pb-10">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <ImageIcon size={24} className="text-blue-600" />
            Gestão de Mídias
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Visualize, filtre e gerencie todos os arquivos de check-ins, odômetros e avarias.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchMedias} className="text-xs h-8 px-3">
          Atualizar
        </Button>
      </div>

      {/* KPI Stats Panel */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-3.5 flex items-center gap-3 bg-gradient-to-br from-blue-50/30 to-white shadow-sm border border-slate-100 rounded-xl">
          <div className="p-2 bg-blue-100/70 text-blue-600 rounded-lg">
            <FolderSimple size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Total</p>
            <h4 className="text-base font-bold text-slate-700 mt-0.5">{medias.length} arquivos</h4>
          </div>
        </Card>
        <Card className="p-3.5 flex items-center gap-3 bg-gradient-to-br from-emerald-50/30 to-white shadow-sm border border-slate-100 rounded-xl">
          <div className="p-2 bg-emerald-100/70 text-emerald-600 rounded-lg">
            <Info size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Espaço</p>
            <h4 className="text-base font-bold text-slate-700 mt-0.5">{totalSizeMB} MB</h4>
          </div>
        </Card>
        <Card className="p-3.5 flex items-center gap-3 bg-gradient-to-br from-purple-50/30 to-white shadow-sm border border-slate-100 rounded-xl">
          <div className="p-2 bg-purple-100/70 text-purple-600 rounded-lg">
            <Clock size={20} />
          </div>
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Exibidos</p>
            <h4 className="text-base font-bold text-slate-700 mt-0.5">{filtered.length} arquivos</h4>
          </div>
        </Card>
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col gap-3 bg-slate-50/50 p-3.5 rounded-xl border border-slate-100">
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          {/* Busca por texto */}
          <div className="relative w-full sm:max-w-xs">
            <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <Input
              placeholder="Buscar arquivo..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 text-xs h-8"
            />
          </div>

          {/* Selecionar Todos / Ações em lote rápidas */}
          {filtered.some(m => DELETABLE_CONTEXTS.includes(m.contexto)) && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSelectAllEligible}
              className="text-xs h-8 w-full sm:w-auto px-3 border-dashed hover:bg-slate-100"
            >
              {filtered.filter(m => DELETABLE_CONTEXTS.includes(m.contexto)).every(m => isSelected(m))
                ? 'Desmarcar Todos'
                : 'Selecionar Todos Elegíveis'}
            </Button>
          )}
        </div>

        {/* Categorias / Quick Filter Pills */}
        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-100/50">
          {[
            { id: 'all', label: 'Todas as Mídias' },
            { id: 'comprovante', label: 'Auditoria (Comprovantes)' },
            { id: 'vistoria', label: 'Conferência (Vistoria)' },
            { id: 'odometros', label: 'Odômetros' },
            { id: 'sinistro', label: 'Avarias' },
            { id: 'protected', label: '🔒 Protegidos (Veículos, CNH, CRLV)' },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setQuickFilter(pill.id)}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all duration-150 ${
                quickFilter === pill.id
                  ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid de Miniaturas Compactas */}
      {loading ? (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-3">
          {Array.from({ length: 16 }).map((_, i) => (
            <Card key={i} className="aspect-square p-1.5 border border-slate-100 shadow-sm rounded-lg flex flex-col justify-between">
              <Skeleton className="h-full w-full rounded-md" />
            </Card>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-10 text-center text-muted-foreground flex flex-col items-center justify-center space-y-3 border-dashed border-2 border-slate-200 max-w-xl mx-auto mt-6 rounded-2xl">
          <div className="p-3 bg-slate-50 rounded-full">
            <ImageIcon size={28} className="text-slate-400" />
          </div>
          <div className="space-y-1">
            <div className="font-semibold text-slate-700 text-xs">Nenhum Arquivo Encontrado</div>
            <p className="text-[11px] text-slate-400 max-w-xs">
              Não existem mídias carregadas com os filtros selecionados no momento.
            </p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-3">
          {filtered.map((m, idx) => {
            const isPdf = m.filename.toLowerCase().endsWith('.pdf');
            const fileUrl = getFullUrl(m.url);
            const isDeletable = DELETABLE_CONTEXTS.includes(m.contexto);
            const selected = isSelected(m);

            return (
              <div
                key={idx}
                onClick={() => handleOpenPreview(m)}
                className={`relative aspect-square rounded-xl overflow-hidden border bg-slate-50 flex flex-col justify-between group cursor-pointer transition-all duration-200 ${
                  selected
                    ? 'border-blue-500 ring-2 ring-blue-500/25 shadow-md'
                    : 'border-slate-200 hover:border-slate-300 shadow-sm'
                }`}
              >
                {/* Visualizador de PDF ou Imagem */}
                <div className="absolute inset-0 flex items-center justify-center bg-slate-100">
                  {isPdf ? (
                    <div className="flex flex-col items-center gap-1 text-red-500">
                      <FilePdf size={36} weight="duotone" />
                      <span className="text-[8px] font-bold text-slate-500 uppercase">PDF</span>
                    </div>
                  ) : (
                    <img
                      src={fileUrl}
                      alt={m.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                    />
                  )}
                </div>

                {/* Overlay Topo: Checkbox ou Lock */}
                <div className="absolute top-1.5 left-1.5 z-10">
                  {isDeletable ? (
                    <div
                      onClick={(e) => handleToggleSelect(m, e)}
                      className={`w-5 h-5 rounded-full flex items-center justify-center border transition-all ${
                        selected
                          ? 'bg-blue-600 border-blue-600 text-white shadow-smScale'
                          : 'bg-white/90 backdrop-blur-sm border-slate-300 text-transparent hover:border-blue-500 hover:text-slate-300'
                      }`}
                    >
                      <Check size={10} weight="bold" className={selected ? 'block' : 'group-hover:block'} />
                    </div>
                  ) : (
                    <div
                      className="w-5 h-5 rounded-full bg-slate-900/60 backdrop-blur-sm flex items-center justify-center text-white"
                      title="Arquivo Protegido (Exclusão Desativada)"
                    >
                      <Lock size={10} weight="fill" />
                    </div>
                  )}
                </div>

                {/* Badge Contexto (Tag minimalista no topo direito) */}
                <div className="absolute top-1.5 right-1.5 z-10">
                  <span className={`text-[8px] font-extrabold uppercase px-1.5 py-0.5 rounded-full backdrop-blur-md border border-white/20 shadow-sm ${CONTEXTO_COLORS[m.contexto] || 'bg-slate-100 text-slate-700'}`}>
                    {m.contexto === 'km_inicial' || m.contexto === 'km_final' ? 'KM' : CONTEXTO_LABELS[m.contexto]?.split(' ')[0] || m.contexto}
                  </span>
                </div>

                {/* Rodapé Minimalista: Nome e tamanho */}
                <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-slate-950/80 via-slate-900/50 to-transparent p-1.5 pt-4 text-white z-10 flex flex-col justify-end">
                  <div className="text-[9px] font-medium truncate" title={m.filename}>
                    {m.filename}
                  </div>
                  <div className="text-[8px] text-slate-300 font-mono mt-0.5">
                    {formatBytes(m.tamanho_bytes)}
                  </div>
                </div>

                {/* Overlay de Hover para Ações Rápidas */}
                <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition-opacity z-20 flex items-center justify-center gap-1.5">
                  <div className="p-1.5 bg-white text-slate-800 rounded-full hover:bg-slate-100 shadow transition-colors" title="Visualizar Detalhes">
                    <Info size={14} />
                  </div>
                  <a
                    href={fileUrl}
                    download={m.filename}
                    onClick={(e) => e.stopPropagation()}
                    className="p-1.5 bg-blue-600 text-white rounded-full hover:bg-blue-700 shadow transition-colors"
                    title="Download"
                  >
                    <DownloadSimple size={14} />
                  </a>
                  {isDeletable && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteSingle(m.contexto, m.filename);
                      }}
                      className="p-1.5 bg-red-600 text-white rounded-full hover:bg-red-700 shadow transition-colors"
                      title="Excluir"
                    >
                      <Trash size={14} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Barra de Ações em Lote (Fixa ao selecionar itens) */}
      {selectedItems.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-white/90 backdrop-blur-md shadow-2xl border border-slate-200 px-5 py-3 rounded-2xl flex items-center gap-6 z-[90] animate-in fade-in slide-in-from-bottom-5 duration-200">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold">
              {selectedItems.length}
            </div>
            <span className="text-xs font-semibold text-slate-700">Mídias selecionadas</span>
          </div>

          <div className="h-4 w-[1px] bg-slate-200" />

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedItems([])}
              className="text-xs text-slate-500 hover:text-slate-800 h-8 px-2.5"
            >
              Cancelar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBulkDelete}
              className="text-xs font-bold bg-red-600 hover:bg-red-700 flex items-center gap-1.5 h-8 px-3"
            >
              <Trash size={14} />
              Excluir Selecionadas
            </Button>
          </div>
        </div>
      )}

      {/* Lightbox / Modal de Visualização Expandida */}
      {previewIndex !== null && previewItem && (
        <div 
          className="fixed inset-0 bg-slate-950/95 backdrop-blur-md z-[100] flex items-center justify-center p-4 md:p-6 animate-in fade-in duration-200"
          onClick={() => setPreviewIndex(null)}
        >
          {/* Botão de Fechar */}
          <button
            onClick={() => setPreviewIndex(null)}
            className="absolute top-4 right-4 text-white hover:text-slate-300 p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-[110]"
          >
            <X size={20} />
          </button>

          {/* Seta Esquerda */}
          <button
            onClick={handlePrev}
            className="absolute left-6 top-1/2 -translate-y-1/2 text-white hover:text-slate-300 p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-[110] hidden md:block"
          >
            <CaretLeft size={24} weight="bold" />
          </button>

          {/* Seta Direita */}
          <button
            onClick={handleNext}
            className="absolute right-6 top-1/2 -translate-y-1/2 text-white hover:text-slate-300 p-3 rounded-full bg-white/10 hover:bg-white/20 transition-colors z-[110] hidden md:block"
          >
            <CaretRight size={24} weight="bold" />
          </button>

          {/* Conteúdo Principal do Modal */}
          <div
            className="relative max-w-4xl w-full max-h-[85vh] flex flex-col md:flex-row bg-white rounded-2xl overflow-hidden shadow-2xl z-[105] animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Lado Esquerdo: Imagem / PDF */}
            <div className="flex-1 bg-slate-950 flex items-center justify-center min-h-[300px] md:min-h-[480px] relative select-none">
              {previewItem.filename.toLowerCase().endsWith('.pdf') ? (
                <div className="flex flex-col items-center gap-4 text-red-500 p-10">
                  <FilePdf size={72} weight="duotone" />
                  <span className="text-sm font-semibold text-slate-300">Documento PDF</span>
                  <a
                    href={getFullUrl(previewItem.url)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 mt-2 underline"
                  >
                    Abrir em nova guia
                    <ArrowSquareOut size={14} />
                  </a>
                </div>
              ) : (
                <img
                  src={getFullUrl(previewItem.url)}
                  alt={previewItem.filename}
                  className="max-w-full max-h-[80vh] md:max-h-[485px] object-contain"
                />
              )}
            </div>

            {/* Lado Direito: Informações e Metadados */}
            <div className="w-full md:w-72 p-5 flex flex-col justify-between border-l border-slate-100 bg-white">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Badge variant="outline" className={`text-[10px] font-bold uppercase ${CONTEXTO_COLORS[previewItem.contexto] || 'bg-slate-100 text-slate-700'}`}>
                    {CONTEXTO_LABELS[previewItem.contexto] || previewItem.contexto}
                  </Badge>
                  <h3 className="text-sm font-bold text-slate-800 break-all leading-snug">
                    {previewItem.filename}
                  </h3>
                </div>

                <div className="h-[1px] bg-slate-100" />

                {/* Detalhes específicos */}
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center text-slate-500">
                    <span className="flex items-center gap-1.5"><Calendar size={14} /> Data:</span>
                    <span className="font-semibold text-slate-700">
                      {previewItem.data_criacao ? new Date(previewItem.data_criacao).toLocaleString('pt-BR') : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-slate-500">
                    <span className="flex items-center gap-1.5"><Info size={14} /> Tamanho:</span>
                    <span className="font-mono font-semibold text-slate-700">
                      {formatBytes(previewItem.tamanho_bytes)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-slate-500">
                    <span className="flex items-center gap-1.5"><Lock size={14} /> Status:</span>
                    <span className={`font-bold ${DELETABLE_CONTEXTS.includes(previewItem.contexto) ? 'text-green-600' : 'text-amber-600'}`}>
                      {DELETABLE_CONTEXTS.includes(previewItem.contexto) ? 'Deletável' : '🔒 Protegido'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Botões de Ação */}
              <div className="space-y-2.5 pt-4 border-t border-slate-100 mt-6">
                <div className="flex gap-2">
                  {/* Setas de navegação para celular */}
                  <Button variant="outline" size="sm" onClick={handlePrev} className="flex-1 md:hidden h-9">
                    <CaretLeft size={16} />
                  </Button>
                  <a
                    href={getFullUrl(previewItem.url)}
                    download={previewItem.filename}
                    className="flex-[2] text-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Button variant="outline" size="sm" className="w-full text-xs h-9 flex items-center justify-center gap-1.5">
                      <DownloadSimple size={16} />
                      Baixar
                    </Button>
                  </a>
                  <Button variant="outline" size="sm" onClick={handleNext} className="flex-1 md:hidden h-9">
                    <CaretRight size={16} />
                  </Button>
                </div>

                {DELETABLE_CONTEXTS.includes(previewItem.contexto) ? (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleDeleteFromPreview}
                    className="w-full text-xs bg-red-600 hover:bg-red-700 h-9 flex items-center justify-center gap-1.5"
                  >
                    <Trash size={16} />
                    Excluir Arquivo
                  </Button>
                ) : (
                  <div className="bg-slate-50 text-[10px] text-slate-400 p-2 rounded-lg text-center flex items-center justify-center gap-1">
                    <Lock size={12} weight="fill" />
                    Este arquivo do sistema não pode ser removido.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
