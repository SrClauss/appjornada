import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog';
import { Wrench, CurrencyDollar, Clock, TrendUp, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useManutencoes, useCreateManutencao, useUpdateManutencao } from '@/hooks/useManutencoes';
import type { CreateManutencaoPayload, Manutencao, MaintenanceStatus } from '@/lib/types';

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export function ManutencoesView() {
  const { data: manutencoes = [], isLoading } = useManutencoes();
  const createMutation = useCreateManutencao();
  const updateMutation = useUpdateManutencao();
  const [openCreate, setOpenCreate] = useState(false);

  const [form, setForm] = useState<CreateManutencaoPayload>({
    veiculo_id: '', oficina: '', km: 0,
    servico: { tipo: '', descricao: '', valor: 0 },
  });

  const totalCost    = manutencoes.reduce((s, m) => s + (m.servico?.valor ?? 0), 0);
  const inProgress   = manutencoes.filter((m) => m.status === 'EM_ANDAMENTO').length;
  const completed    = manutencoes.filter((m) => m.status === 'CONCLUIDA').length;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync(form);
      toast.success('Manutenção registrada!');
      setOpenCreate(false);
      setForm({ veiculo_id: '', oficina: '', km: 0, servico: { tipo: '', descricao: '', valor: 0 } });
    } catch {
      toast.error('Erro ao registrar manutenção.');
    }
  };

  const handleStatusToggle = async (m: Manutencao) => {
    const novoStatus: MaintenanceStatus =
      m.status === 'EM_ANDAMENTO' ? 'CONCLUIDA' : 'EM_ANDAMENTO';
    try {
      await updateMutation.mutateAsync({ id: m.id, payload: { status: novoStatus } });
      toast.success('Status atualizado!');
    } catch {
      toast.error('Erro ao atualizar status.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Manutenções</h1>
          <p className="text-muted-foreground mt-1">Controle de manutenções da frota</p>
        </div>
        <Button onClick={() => setOpenCreate(true)}>
          <Plus size={16} className="mr-1" /> Nova Manutenção
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-destructive/10 rounded-lg">
                <CurrencyDollar className="text-destructive" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Gasto Total</p>
                <p className="text-2xl font-semibold">{formatCurrency(totalCost)}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-warning/10 rounded-lg">
                <Clock className="text-warning" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Em Andamento</p>
                <p className="text-2xl font-semibold">{inProgress}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-success/10 rounded-lg">
                <Wrench className="text-success" size={24} />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Concluídas</p>
                <p className="text-2xl font-semibold">{completed}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Histórico de Manutenções</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Entrada</TableHead>
                    <TableHead>Veículo</TableHead>
                    <TableHead>Oficina</TableHead>
                    <TableHead>Tipo Serviço</TableHead>
                    <TableHead>Descrição</TableHead>
                    <TableHead>Valor</TableHead>
                    <TableHead>Km</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {manutencoes.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                        Nenhuma manutenção registrada.
                      </TableCell>
                    </TableRow>
                  ) : (
                    manutencoes.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell>
                          {m.entrada
                            ? new Date(m.entrada).toLocaleDateString('pt-BR')
                            : '—'}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{m.veiculo_id}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">{m.oficina ?? '—'}</TableCell>
                        <TableCell className="text-sm">{m.servico?.tipo ?? '—'}</TableCell>
                        <TableCell className="text-sm max-w-xs truncate">
                          {m.servico?.descricao ?? '—'}
                        </TableCell>
                        <TableCell className="font-semibold">
                          {m.servico?.valor ? formatCurrency(m.servico.valor) : '—'}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {m.km?.toLocaleString() ?? '—'}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={m.status === 'EM_ANDAMENTO' ? 'default' : 'secondary'}
                          >
                            {m.status === 'EM_ANDAMENTO' ? 'Em Andamento' : 'Concluída'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStatusToggle(m)}
                            disabled={updateMutation.isPending}
                          >
                            {m.status === 'EM_ANDAMENTO' ? 'Concluir' : 'Reabrir'}
                          </Button>
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

      {/* Modal nova manutenção */}
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nova Manutenção</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label>Placa do Veículo</Label>
              <Input
                required
                placeholder="TST1A23"
                value={form.veiculo_id}
                onChange={(e) => setForm({ ...form, veiculo_id: e.target.value.toUpperCase() })}
              />
            </div>
            <div className="space-y-2">
              <Label>Oficina</Label>
              <Input
                placeholder="Nome da oficina"
                value={form.oficina}
                onChange={(e) => setForm({ ...form, oficina: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Km no Momento</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.km}
                  onChange={(e) => setForm({ ...form, km: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Km Próxima Revisão</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.km_proxima_revisao}
                  onChange={(e) =>
                    setForm({ ...form, km_proxima_revisao: Number(e.target.value) })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Tipo de Serviço</Label>
              <Input
                placeholder="Troca de óleo, revisão, pneu..."
                value={form.servico?.tipo}
                onChange={(e) =>
                  setForm({ ...form, servico: { ...form.servico, tipo: e.target.value } })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Descrição</Label>
              <Input
                placeholder="Detalhes do serviço"
                value={form.servico?.descricao}
                onChange={(e) =>
                  setForm({ ...form, servico: { ...form.servico, descricao: e.target.value } })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Valor (R$)</Label>
              <Input
                type="number"
                min={0}
                step="0.01"
                value={form.servico?.valor}
                onChange={(e) =>
                  setForm({
                    ...form,
                    servico: { ...form.servico, valor: Number(e.target.value) },
                  })
                }
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenCreate(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Registrando...' : 'Registrar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

