import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { FileText, Upload, ChartBar } from '@phosphor-icons/react';
import { toast } from 'sonner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useComparativo, useImportarCSV } from '@/hooks/useRelatorios';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export function RelatoriosView() {
  const [activeTab, setActiveTab] = useState('comparativo');
  const [dataFiltro, setDataFiltro] = useState('');
  const [plataforma, setPlataforma] = useState<'uber' | '99'>('uber');
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: comparativo = [], isLoading: loadingComp } = useComparativo(dataFiltro || undefined);
  const importarMutation = useImportarCSV();

  const chartData = comparativo.map((item) => ({
    name: item.motorista_nome,
    Uber: item.corridas_uber ?? 0,
    '99': item.corridas_99 ?? 0,
    Km: item.total_km ?? 0,
  }));

  const handleImport = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { toast.error('Selecione um arquivo CSV.'); return; }
    try {
      const res = await importarMutation.mutateAsync({ plataforma, file });
      toast.success(`Importado: ${res.inseridos ?? 0} registros.`);
      if (fileRef.current) fileRef.current.value = '';
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Erro ao importar CSV.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Relatórios</h1>
        <p className="text-muted-foreground mt-1">Análise de desempenho e histórico</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="comparativo">
            <ChartBar size={16} className="mr-1" /> Comparativo
          </TabsTrigger>
          <TabsTrigger value="importar">
            <Upload size={16} className="mr-1" /> Importar CSV
          </TabsTrigger>
        </TabsList>

        {/* Tab Comparativo */}
        <TabsContent value="comparativo" className="space-y-6 mt-4">
          <div className="flex items-end gap-4">
            <div className="space-y-1">
              <Label>Filtrar por data</Label>
              <Input
                type="date"
                value={dataFiltro}
                onChange={(e) => setDataFiltro(e.target.value)}
                className="w-48"
              />
            </div>
            {dataFiltro && (
              <Button variant="outline" onClick={() => setDataFiltro('')}>
                Limpar
              </Button>
            )}
          </div>

          {loadingComp ? (
            <Skeleton className="h-64 w-full rounded-xl" />
          ) : (
            <Card>
              <CardHeader><CardTitle>Corridas por Motorista</CardTitle></CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="Uber" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="99" fill="hsl(var(--accent))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader><CardTitle>Detalhamento</CardTitle></CardHeader>
            <CardContent>
              {loadingComp ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Motorista</TableHead>
                        <TableHead>Data</TableHead>
                        <TableHead>Corridas Uber</TableHead>
                        <TableHead>Corridas 99</TableHead>
                        <TableHead>KM Total</TableHead>
                        <TableHead>Faturamento</TableHead>
                        <TableHead>Fonte</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {comparativo.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={7}
                            className="text-center text-muted-foreground py-8"
                          >
                            Nenhum dado disponível.
                          </TableCell>
                        </TableRow>
                      ) : (
                        comparativo.map((item, i) => (
                          <TableRow key={i}>
                            <TableCell className="font-medium">{item.motorista_nome}</TableCell>
                            <TableCell>
                              {item.data
                                ? new Date(item.data).toLocaleDateString('pt-BR')
                                : '—'}
                            </TableCell>
                            <TableCell>{item.corridas_uber ?? '—'}</TableCell>
                            <TableCell>{item.corridas_99 ?? '—'}</TableCell>
                            <TableCell className="font-mono">
                              {item.total_km?.toLocaleString('pt-BR') ?? '—'}
                            </TableCell>
                            <TableCell className="font-semibold">
                              {item.faturamento ? formatCurrency(item.faturamento) : '—'}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">{item.fonte ?? 'jornada'}</Badge>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab Importar CSV */}
        <TabsContent value="importar" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText size={20} />
                Importar Relatório CSV
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6 max-w-md">
              <div className="space-y-2">
                <Label>Plataforma</Label>
                <Select
                  value={plataforma}
                  onValueChange={(v) => setPlataforma(v as 'uber' | '99')}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="uber">Uber</SelectItem>
                    <SelectItem value="99">99</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Arquivo CSV</Label>
                <Input ref={fileRef} type="file" accept=".csv" />
                <p className="text-xs text-muted-foreground">
                  Use o formato exportado pela plataforma.
                </p>
              </div>

              <Button
                onClick={handleImport}
                disabled={importarMutation.isPending}
                className="w-full"
              >
                <Upload size={16} className="mr-2" />
                {importarMutation.isPending ? 'Importando...' : 'Importar'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

