import { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, startOfMonth } from 'date-fns';
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
import { FileText, Upload, ChartBar, Medal } from '@phosphor-icons/react';
import { toast } from 'sonner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts';
import { useComparativo, useImportarCSV } from '@/hooks/useRelatorios';
import api from '@/lib/api';
import type { Jornada } from '@/lib/types';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const RADAR_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

function normalize(value: number, min: number, max: number) {
  if (max === min) return 0;
  return Math.round(((value - min) / (max - min)) * 100);
}

export function RelatoriosView() {
  const [activeTab, setActiveTab] = useState('comparativo');
  const [dataFiltro, setDataFiltro] = useState('');
  const [plataforma, setPlataforma] = useState<'uber' | '99'>('uber');
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: comparativo = [], isLoading: loadingComp } = useComparativo(dataFiltro || undefined);
  const importarMutation = useImportarCSV();

  // Dados de desempenho mensal
  const mesAtual = format(startOfMonth(new Date()), 'yyyy-MM-dd');
  const { data: jornadasMes = [], isLoading: loadingDesempenho } = useQuery({
    queryKey: ['relatorios', 'desempenho', mesAtual],
    queryFn: async () => {
      const { data } = await api.get<Jornada[]>('/jornadas', { params: { limit: 200 } });
      return data.filter((j) => j.data >= mesAtual);
    },
    staleTime: 120_000,
  });

  const driverStats = (() => {
    const map: Record<string, { horas: number; km: number; fat: number; count: number }> = {};
    for (const j of jornadasMes) {
      const nome = j.motorista_nome ?? j.motorista_id;
      if (!map[nome]) map[nome] = { horas: 0, km: 0, fat: 0, count: 0 };
      map[nome].horas += (j.horario?.total_horas_segundos ?? 0) / 3600;
      map[nome].km += j.km?.rodados ?? 0;
      map[nome].fat += j.faturamento?.total_dia ?? 0;
      map[nome].count++;
    }
    return Object.entries(map).map(([nome, s]) => ({
      nome,
      horas: Math.round(s.horas * 10) / 10,
      km: Math.round(s.km),
      fat: Math.round(s.fat * 100) / 100,
    }));
  })();

  const maxHoras = Math.max(...driverStats.map((d) => d.horas), 1);
  const maxKm = Math.max(...driverStats.map((d) => d.km), 1);
  const maxFat = Math.max(...driverStats.map((d) => d.fat), 1);

  const driverStatsNorm = driverStats.map((d) => ({
    ...d,
    score: Math.round(
      (normalize(d.horas, 0, maxHoras) + normalize(d.km, 0, maxKm) + normalize(d.fat, 0, maxFat)) / 3,
    ),
  })).sort((a, b) => b.score - a.score);

  // Dados do RadarChart: 3 eixos (Horas, KM, Faturamento), uma linha por motorista
  const RADAR_SUBJECTS = ['Horas', 'KM', 'Faturamento'];
  const radarData = RADAR_SUBJECTS.map((subject) => {
    const entry: Record<string, string | number> = { subject };
    for (const d of driverStats) {
      const key = d.nome.split(' ')[0];
      if (subject === 'Horas') entry[key] = normalize(d.horas, 0, maxHoras);
      if (subject === 'KM') entry[key] = normalize(d.km, 0, maxKm);
      if (subject === 'Faturamento') entry[key] = normalize(d.fat, 0, maxFat);
    }
    return entry;
  });
  const driverNames = driverStats.map((d) => d.nome.split(' ')[0]);

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
          <TabsTrigger value="desempenho">
            <Medal size={16} className="mr-1" /> Desempenho
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

        {/* Tab Desempenho Mensal */}
        <TabsContent value="desempenho" className="space-y-6 mt-4">
          {loadingDesempenho ? (
            <Skeleton className="h-80 w-full rounded-xl" />
          ) : driverStats.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              Nenhum dado de jornada encontrado para este mês.
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">
                    Radar de Desempenho — Mês Atual
                  </h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="subject" tick={{ fontSize: 13 }} />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                      {driverNames.map((name, idx) => (
                        <Radar
                          key={name}
                          name={name}
                          dataKey={name}
                          stroke={RADAR_COLORS[idx % RADAR_COLORS.length]}
                          fill={RADAR_COLORS[idx % RADAR_COLORS.length]}
                          fillOpacity={0.2}
                        />
                      ))}
                      <Legend />
                      <Tooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </Card>

                <Card className="p-6">
                  <h3 className="text-lg font-semibold mb-4">Faturamento Mensal por Motorista</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={driverStats}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="nome" tickFormatter={(v) => v.split(' ')[0]} tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `R$${v}`} />
                      <Tooltip formatter={(v) => formatCurrency(Number(v))} />
                      <Bar dataKey="fat" fill="hsl(var(--primary))" name="Faturamento" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Medal size={20} /> Ranking de Desempenho
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Posição</TableHead>
                        <TableHead>Motorista</TableHead>
                        <TableHead>Horas</TableHead>
                        <TableHead>KM</TableHead>
                        <TableHead>Faturamento</TableHead>
                        <TableHead>Score</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {driverStatsNorm.map((d, i) => (
                        <TableRow key={d.nome}>
                          <TableCell>
                            <Badge
                              variant={i === 0 ? 'default' : i === 1 ? 'secondary' : 'outline'}
                            >
                              #{i + 1}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-medium">{d.nome}</TableCell>
                          <TableCell>{d.horas}h</TableCell>
                          <TableCell>{d.km.toLocaleString('pt-BR')} km</TableCell>
                          <TableCell>{formatCurrency(d.fat)}</TableCell>
                          <TableCell>
                            <span className="font-bold text-primary">{d.score}</span>
                            <span className="text-muted-foreground text-xs">/100</span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Tab Importar CSV */}
        <TabsContent value="importar" className="mt-4">          <Card>
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

