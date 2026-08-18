import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, startOfMonth } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { Target, Trophy, CurrencyDollar } from '@phosphor-icons/react';
import { toast } from 'sonner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useMetas, useCreateMeta, useDeleteMeta } from '@/hooks/useMetas';
import api from '@/lib/api';
import type { Jornada, CreateMetaPayload, GoalType, GoalReference } from '@/lib/types';

const formatCurrency = (v?: number | null) => {
  const num = typeof v === 'number' && !isNaN(v) ? v : 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
};

const goalTypeLabel: Record<string, string> = {
  FATURAMENTO_DIA: 'Faturamento Diário',
  KM_MES: 'KM Mensal',
  HORAS_MES: 'Horas Mensais',
  CORRIDAS_PARTICULARES_VALOR: 'Corridas Particulares (Faturamento R$)',
  CORRIDAS_PARTICULARES_QTD: 'Corridas Particulares (Qtd. de Corridas)',
};

const getGoalLabel = (tipo?: string) => {
  if (!tipo) return 'Meta';
  return goalTypeLabel[tipo] || tipo.replace(/_/g, ' ');
};

export function MetasView() {
  const { data: rawMetas = [], isLoading } = useMetas();
  const metas = Array.isArray(rawMetas) ? rawMetas : [];
  const createMutation = useCreateMeta();
  const deleteMutation = useDeleteMeta();
  const [openCreate, setOpenCreate] = useState(false);

  // Busca jornadas do mês para calcular bônus acumulado por motorista
  const mesAtual = format(startOfMonth(new Date()), 'yyyy-MM-dd');
  const { data: rawJornadas } = useQuery({
    queryKey: ['metas', 'jornadas-mes', mesAtual],
    queryFn: async () => {
      try {
        const { data } = await api.get('/jornadas', { params: { limit: 200 } });
        const list = Array.isArray(data) ? data : (data && Array.isArray((data as any).items) ? (data as any).items : []);
        return list.filter((j: any) => j && j.data && j.data >= mesAtual);
      } catch (err) {
        console.error('Erro ao buscar jornadas do mês:', err);
        return [];
      }
    },
    staleTime: 60_000,
  });

  const jornadasMes = Array.isArray(rawJornadas) ? rawJornadas : [];

  const bonusChartData = (() => {
    const map: Record<string, number> = {};
    for (const j of jornadasMes) {
      if (!j) continue;
      const rawNome = j.motorista_nome || j.motorista_id || 'Motorista';
      const nome = String(rawNome).split(' ')[0];
      map[nome] = (map[nome] ?? 0) + (Number(j.bonus_dia) || 0);
    }
    return Object.entries(map).map(([name, bonus]) => ({ name, bonus }));
  })();

  const emptyForm: CreateMetaPayload = {
    tipo: 'FATURAMENTO_DIA',
    referencia: 'GERAL',
    faixa_minima: 0,
    faixa_maxima: 0,
    bonus: 0,
    hora_inicio: undefined,
    hora_fim: undefined,
  };
  const [form, setForm] = useState<CreateMetaPayload>(emptyForm);

  const totalBonus = metas.reduce((s, m) => s + (Number(m.bonus) || 0), 0);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync(form);
      toast.success('Meta criada!');
      setOpenCreate(false);
      setForm(emptyForm);
    } catch {
      toast.error('Erro ao criar meta.');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Excluir esta meta?')) return;
    try {
      await deleteMutation.mutateAsync(id);
      toast.success('Meta excluída.');
    } catch {
      toast.error('Erro ao excluir meta.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Metas & Bônus</h1>
          <p className="text-muted-foreground mt-1">Gestão de metas e incentivos</p>
        </div>
        <Button onClick={() => setOpenCreate(true)}>
          <Target size={20} className="mr-2" /> Nova Meta
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-accent/10 rounded-lg">
                <Target className="text-accent" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Metas Cadastradas</p>
                <p className="text-2xl font-semibold">{metas.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-warning/10 rounded-lg">
                <CurrencyDollar className="text-warning" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Bônus Total Disponível</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalBonus)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-success/10 rounded-lg">
                <Trophy className="text-success" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Metas Gerais</p>
                <p className="text-2xl font-semibold">
                  {metas.filter((m) => m.referencia === 'GERAL').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráfico de bônus acumulado no mês */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Bônus Acumulado no Mês por Motorista</h3>
        {bonusChartData.length === 0 ? (
          <p className="text-muted-foreground text-sm py-8 text-center">
            Nenhum bônus registrado este mês.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={bonusChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `R$${v}`} />
              <Tooltip formatter={(v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })} />
              <Bar dataKey="bonus" fill="#10b981" name="Bônus" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader><CardTitle>Metas Cadastradas</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {metas.length === 0 ? (
                <p className="text-muted-foreground col-span-2 text-center py-8">
                  Nenhuma meta cadastrada.
                </p>
              ) : (
                metas.map((goal) => (
                  <Card key={goal.id} className="border-2">
                    <CardContent className="p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="font-semibold text-lg">{getGoalLabel(goal.tipo)}</h3>
                          <p className="text-sm text-muted-foreground">
                            {goal.referencia === 'GERAL' ? 'Geral' : 'Por Motorista'}
                          </p>
                        </div>
                        <Badge variant="outline">{goal.referencia}</Badge>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Faixa Mínima:</span>
                          <span className="font-semibold">
                            {goal.tipo === 'FATURAMENTO_DIA' || goal.tipo === 'CORRIDAS_PARTICULARES_VALOR'
                              ? formatCurrency(goal.faixa_minima)
                              : goal.tipo === 'CORRIDAS_PARTICULARES_QTD'
                              ? `${goal.faixa_minima} corridas`
                              : goal.faixa_minima}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Faixa Máxima:</span>
                          <span className="font-semibold">
                            {goal.tipo === 'FATURAMENTO_DIA' || goal.tipo === 'CORRIDAS_PARTICULARES_VALOR'
                              ? formatCurrency(goal.faixa_maxima)
                              : goal.tipo === 'CORRIDAS_PARTICULARES_QTD'
                              ? `${goal.faixa_maxima} corridas`
                              : goal.faixa_maxima}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm pt-2 border-t">
                          <span className="text-muted-foreground">Bônus:</span>
                          <span className="font-bold text-success">
                            {formatCurrency(goal.bonus)}
                          </span>
                        </div>
                        {goal.hora_inicio && goal.hora_fim && (
                          <div className="flex justify-between text-sm pt-1.5 text-amber-500 font-medium">
                            <span>Horário Válido:</span>
                            <span>{goal.hora_inicio} às {goal.hora_fim}</span>
                          </div>
                        )}
                      </div>

                      <div className="flex gap-2 mt-4">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          onClick={() => handleDelete(goal.id)}
                          disabled={deleteMutation.isPending}
                        >
                          Excluir
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Modal criar meta */}
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova Meta</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label>Tipo</Label>
              <Select
                value={form.tipo}
                onValueChange={(v) => setForm({ ...form, tipo: v as GoalType })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="FATURAMENTO_DIA">Faturamento Diário (R$)</SelectItem>
                  <SelectItem value="KM_MES">KM Mensal (km)</SelectItem>
                  <SelectItem value="HORAS_MES">Horas Mensais (h)</SelectItem>
                  <SelectItem value="CORRIDAS_PARTICULARES_VALOR">Corridas Particulares (Faturamento R$)</SelectItem>
                  <SelectItem value="CORRIDAS_PARTICULARES_QTD">Corridas Particulares (Qtd. de Corridas)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Referência</Label>
              <Select
                value={form.referencia}
                onValueChange={(v) => setForm({ ...form, referencia: v as GoalReference })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="GERAL">Geral</SelectItem>
                  <SelectItem value="MOTORISTA">Por Motorista</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Faixa Mínima</Label>
                <Input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.faixa_minima}
                  onChange={(e) => setForm({ ...form, faixa_minima: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Faixa Máxima</Label>
                <Input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.faixa_maxima}
                  onChange={(e) => setForm({ ...form, faixa_maxima: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Valor do Bônus (R$)</Label>
              <Input
                type="number"
                required
                min={0}
                step="0.01"
                value={form.bonus}
                onChange={(e) => setForm({ ...form, bonus: Number(e.target.value) })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Hora Início (Opcional)</Label>
                <Input
                  type="time"
                  value={form.hora_inicio || ''}
                  onChange={(e) => setForm({ ...form, hora_inicio: e.target.value || undefined })}
                />
              </div>
              <div className="space-y-2">
                <Label>Hora Fim (Opcional)</Label>
                <Input
                  type="time"
                  value={form.hora_fim || ''}
                  onChange={(e) => setForm({ ...form, hora_fim: e.target.value || undefined })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenCreate(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Criando...' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

