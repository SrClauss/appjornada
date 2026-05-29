import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Files, DownloadSimple, Trash, MagnifyingGlass, Monitor, ArrowLeft, ArrowRight,
} from '@phosphor-icons/react';
import { toast } from 'sonner';
import api from '@/lib/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ArquivoColeta {
  caminho: string;
  package: string;
  data: string;
  nome: string;
  telas: number;
  tamanho_kb: number;
  modificado_em: string;
}

interface TelaUnica {
  package: string;
  activity: string;
  total_capturas: number;
  primeiro_visto: string;
  ultimo_visto: string;
}

interface SnapshotItem {
  packageName?: string;
  activityClass?: string;
  timestamp?: string;
  _dispositivo?: string;
  _recebido_em?: string;
  _arquivo_origem?: string;
  elements?: unknown[];
  [key: string]: unknown;
}

interface SnapshotsResponse {
  total: number;
  skip: number;
  limit: number;
  items: SnapshotItem[];
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

function useArquivos() {
  return useQuery<ArquivoColeta[]>({
    queryKey: ['coleta', 'admin', 'arquivos'],
    queryFn: async () => {
      const { data } = await api.get('/coleta/admin/arquivos');
      return data;
    },
    staleTime: 30_000,
  });
}

function useTelas(packageFiltro?: string) {
  return useQuery<TelaUnica[]>({
    queryKey: ['coleta', 'admin', 'telas', packageFiltro],
    queryFn: async () => {
      const { data } = await api.get('/coleta/admin/telas', {
        params: packageFiltro ? { package: packageFiltro } : undefined,
      });
      return data;
    },
    staleTime: 30_000,
  });
}

function useSnapshots(packageFiltro: string, activityFiltro: string, skip: number) {
  return useQuery<SnapshotsResponse>({
    queryKey: ['coleta', 'admin', 'snapshots', packageFiltro, activityFiltro, skip],
    queryFn: async () => {
      const { data } = await api.get('/coleta/admin/snapshots', {
        params: {
          ...(packageFiltro ? { package: packageFiltro } : {}),
          ...(activityFiltro ? { activity: activityFiltro } : {}),
          skip,
          limit: 20,
        },
      });
      return data;
    },
    staleTime: 30_000,
  });
}

// ─── Subcomponentes ───────────────────────────────────────────────────────────

function ArquivosTab() {
  const { data: arquivos = [], isLoading } = useArquivos();
  const qc = useQueryClient();
  const [busca, setBusca] = useState('');

  const deletarMutation = useMutation({
    mutationFn: (caminho: string) =>
      api.delete('/coleta/admin/arquivo', { params: { caminho } }),
    onSuccess: () => {
      toast.success('Arquivo removido com sucesso');
      qc.invalidateQueries({ queryKey: ['coleta'] });
    },
    onError: () => toast.error('Erro ao remover arquivo'),
  });

  const handleDownload = async (caminho: string, nome: string) => {
    try {
      const response = await api.get(`/coleta/admin/download/${caminho}`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = nome;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Erro ao baixar arquivo');
    }
  };

  const filtrados = arquivos.filter(
    (a) =>
      !busca ||
      a.nome.toLowerCase().includes(busca.toLowerCase()) ||
      a.package.toLowerCase().includes(busca.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <MagnifyingGlass className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
          <Input
            placeholder="Filtrar por arquivo ou package..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary">{filtrados.length} arquivo(s)</Badge>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : filtrados.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Files size={40} className="mx-auto mb-3 opacity-40" />
            <p>Nenhum arquivo encontrado</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-md border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Package</TableHead>
                <TableHead>Data</TableHead>
                <TableHead>Arquivo</TableHead>
                <TableHead className="text-right">Telas</TableHead>
                <TableHead className="text-right">Tamanho</TableHead>
                <TableHead>Recebido em</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtrados.map((arq) => (
                <TableRow key={arq.caminho}>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {arq.package}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{arq.data}</TableCell>
                  <TableCell className="text-sm font-mono max-w-xs truncate" title={arq.nome}>
                    {arq.nome}
                  </TableCell>
                  <TableCell className="text-right text-sm">{arq.telas}</TableCell>
                  <TableCell className="text-right text-sm">{arq.tamanho_kb} KB</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{arq.modificado_em}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Baixar .jsonl"
                        onClick={() => handleDownload(arq.caminho, arq.nome)}
                      >
                        <DownloadSimple size={16} />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button variant="ghost" size="icon" className="text-destructive" title="Remover arquivo">
                            <Trash size={16} />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Remover arquivo?</AlertDialogTitle>
                            <AlertDialogDescription>
                              O arquivo <strong>{arq.nome}</strong> e todos os seus snapshots no banco serão
                              removidos permanentemente.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancelar</AlertDialogCancel>
                            <AlertDialogAction
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              onClick={() => deletarMutation.mutate(arq.caminho)}
                            >
                              Remover
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function TelasTab() {
  const [packageFiltro, setPackageFiltro] = useState('');
  const [inputPackage, setInputPackage] = useState('');
  const { data: telas = [], isLoading } = useTelas(packageFiltro || undefined);

  const handleExportCSV = async () => {
    try {
      const response = await api.get('/coleta/admin/export-csv', {
        params: packageFiltro ? { package: packageFiltro } : undefined,
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `coleta_export_${packageFiltro || 'todos'}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Erro ao exportar CSV');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Label htmlFor="pkg-filter" className="text-sm whitespace-nowrap">
            Package:
          </Label>
          <Input
            id="pkg-filter"
            placeholder="ex: com.taxis99"
            value={inputPackage}
            onChange={(e) => setInputPackage(e.target.value)}
            className="w-56"
            onKeyDown={(e) => e.key === 'Enter' && setPackageFiltro(inputPackage)}
          />
          <Button variant="outline" size="sm" onClick={() => setPackageFiltro(inputPackage)}>
            Filtrar
          </Button>
          {packageFiltro && (
            <Button variant="ghost" size="sm" onClick={() => { setPackageFiltro(''); setInputPackage(''); }}>
              Limpar
            </Button>
          )}
        </div>
        <div className="ml-auto">
          <Button variant="outline" size="sm" onClick={handleExportCSV}>
            <DownloadSimple size={16} className="mr-2" />
            Exportar CSV
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
        </div>
      ) : telas.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Monitor size={40} className="mx-auto mb-3 opacity-40" />
            <p>Nenhuma tela capturada ainda</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-md border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Package</TableHead>
                <TableHead>Activity / Tela</TableHead>
                <TableHead className="text-right">Capturas</TableHead>
                <TableHead>Primeiro visto</TableHead>
                <TableHead>Último visto</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {telas.map((tela) => (
                <TableRow key={`${tela.package}::${tela.activity}`}>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {tela.package ?? '—'}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs max-w-sm truncate" title={tela.activity}>
                    {tela.activity ?? '—'}
                  </TableCell>
                  <TableCell className="text-right font-semibold">{tela.total_capturas}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{tela.primeiro_visto ?? '—'}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{tela.ultimo_visto ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function SnapshotsTab() {
  const [packageFiltro, setPackageFiltro] = useState('');
  const [activityFiltro, setActivityFiltro] = useState('');
  const [inputPackage, setInputPackage] = useState('');
  const [inputActivity, setInputActivity] = useState('');
  const [skip, setSkip] = useState(0);
  const LIMIT = 20;

  const { data, isLoading } = useSnapshots(packageFiltro, activityFiltro, skip);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  const aplicarFiltros = () => {
    setSkip(0);
    setPackageFiltro(inputPackage);
    setActivityFiltro(inputActivity);
  };

  const limparFiltros = () => {
    setInputPackage('');
    setInputActivity('');
    setPackageFiltro('');
    setActivityFiltro('');
    setSkip(0);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <Label className="text-xs mb-1 block">Package</Label>
          <Input
            placeholder="ex: com.uber.driver"
            value={inputPackage}
            onChange={(e) => setInputPackage(e.target.value)}
            className="w-48"
            onKeyDown={(e) => e.key === 'Enter' && aplicarFiltros()}
          />
        </div>
        <div>
          <Label className="text-xs mb-1 block">Activity</Label>
          <Input
            placeholder="ex: TripActivity"
            value={inputActivity}
            onChange={(e) => setInputActivity(e.target.value)}
            className="w-56"
            onKeyDown={(e) => e.key === 'Enter' && aplicarFiltros()}
          />
        </div>
        <Button variant="outline" size="sm" onClick={aplicarFiltros}>
          <MagnifyingGlass size={14} className="mr-1" /> Buscar
        </Button>
        {(packageFiltro || activityFiltro) && (
          <Button variant="ghost" size="sm" onClick={limparFiltros}>
            Limpar
          </Button>
        )}
        <span className="ml-auto text-sm text-muted-foreground">
          {total} snapshot(s)
        </span>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
        </div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Monitor size={40} className="mx-auto mb-3 opacity-40" />
            <p>Nenhum snapshot encontrado</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="rounded-md border overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Package</TableHead>
                  <TableHead>Activity</TableHead>
                  <TableHead>Dispositivo</TableHead>
                  <TableHead className="text-right">Elementos</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((snap, idx) => (
                  <TableRow key={idx}>
                    <TableCell className="text-sm font-mono">{snap.timestamp ?? '—'}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {snap.packageName ?? '—'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs font-mono max-w-xs truncate" title={snap.activityClass}>
                      {snap.activityClass ?? '—'}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{snap._dispositivo ?? '—'}</TableCell>
                    <TableCell className="text-right text-sm">
                      {Array.isArray(snap.elements) ? snap.elements.length : '—'}
                    </TableCell>
                    <TableCell>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="ghost" size="sm" className="text-xs">
                            Ver JSON
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="max-w-3xl max-h-[80vh]">
                          <DialogHeader>
                            <DialogTitle className="font-mono text-sm truncate">
                              {snap.activityClass ?? 'Snapshot'}
                            </DialogTitle>
                          </DialogHeader>
                          <ScrollArea className="h-[60vh] rounded border bg-muted/50 p-3">
                            <pre className="text-xs whitespace-pre-wrap break-all">
                              {JSON.stringify(snap, null, 2)}
                            </pre>
                          </ScrollArea>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-fit"
                            onClick={() => {
                              const blob = new Blob([JSON.stringify(snap, null, 2)], { type: 'application/json' });
                              const url = URL.createObjectURL(blob);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `snapshot_${snap.timestamp ?? 'export'}.json`;
                              a.click();
                              URL.revokeObjectURL(url);
                            }}
                          >
                            <DownloadSimple size={14} className="mr-1" /> Baixar JSON
                          </Button>
                        </DialogContent>
                      </Dialog>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Paginação */}
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              Exibindo {skip + 1}–{Math.min(skip + LIMIT, total)} de {total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={skip === 0}
                onClick={() => setSkip(Math.max(0, skip - LIMIT))}
              >
                <ArrowLeft size={14} className="mr-1" /> Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={skip + LIMIT >= total}
                onClick={() => setSkip(skip + LIMIT)}
              >
                Próximo <ArrowRight size={14} className="ml-1" />
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ─── View principal ───────────────────────────────────────────────────────────

export function ColetaView() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Coleta de Dados</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Gerencie os snapshots enviados pelo app Android de coleta
        </p>
      </div>

      <Tabs defaultValue="arquivos">
        <TabsList className="mb-4">
          <TabsTrigger value="arquivos">
            <Files size={15} className="mr-2" />
            Arquivos
          </TabsTrigger>
          <TabsTrigger value="telas">
            <Monitor size={15} className="mr-2" />
            Telas únicas
          </TabsTrigger>
          <TabsTrigger value="snapshots">
            <MagnifyingGlass size={15} className="mr-2" />
            Snapshots
          </TabsTrigger>
        </TabsList>

        <TabsContent value="arquivos">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Arquivos .jsonl recebidos</CardTitle>
            </CardHeader>
            <CardContent>
              <ArquivosTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="telas">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Telas / Activities capturadas</CardTitle>
            </CardHeader>
            <CardContent>
              <TelasTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="snapshots">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Snapshots individuais</CardTitle>
            </CardHeader>
            <CardContent>
              <SnapshotsTab />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
