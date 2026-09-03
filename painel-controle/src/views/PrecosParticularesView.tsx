import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { CurrencyDollar, Plus, Trash, PencilSimple } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

interface PrecoParticular {
  _id?: string;
  nome: string;
  hora_inicio: string;
  hora_fim: string;
  preco_km: number;
  preco_minuto: number;
  preco_minimo?: number;
}

export function PrecosParticularesView() {
  const { user } = useAuth();
  const isGestorOrAdmin = user?.role === 'ADMIN' || user?.role === 'GESTOR';

  const [precos, setPrecos] = useState<PrecoParticular[]>([]);
  const [loadingPrecos, setLoadingPrecos] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [precoForm, setPrecoForm] = useState({
    nome: '',
    hora_inicio: '06:00',
    hora_fim: '18:00',
    preco_km: 2.0,
    preco_minuto: 0.5,
    preco_minimo: 0.0,
  });

  const fetchPrecos = async () => {
    if (!isGestorOrAdmin) return;
    setLoadingPrecos(true);
    try {
      const res = await api.get('/config/precos-particulares');
      setPrecos(res.data);
    } catch (err) {
      console.error(err);
      toast.error('Erro ao carregar faixas de preço.');
    } finally {
      setLoadingPrecos(false);
    }
  };

  useEffect(() => {
    fetchPrecos();
  }, [user]);

  const handleOpenCreate = () => {
    setEditingId(null);
    setPrecoForm({
      nome: '',
      hora_inicio: '06:00',
      hora_fim: '18:00',
      preco_km: 2.0,
      preco_minuto: 0.5,
      preco_minimo: 0.0,
    });
    setDialogOpen(true);
  };

  const handleOpenEdit = (p: PrecoParticular) => {
    setEditingId(p._id || null);
    setPrecoForm({
      nome: p.nome,
      hora_inicio: p.hora_inicio,
      hora_fim: p.hora_fim,
      preco_km: p.preco_km,
      preco_minuto: p.preco_minuto,
      preco_minimo: p.preco_minimo ?? 0.0,
    });
    setDialogOpen(true);
  };

  const handleSavePreco = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.put(`/config/precos-particulares/${editingId}`, precoForm);
        toast.success('Faixa de preço atualizada!');
      } else {
        await api.post('/config/precos-particulares', precoForm);
        toast.success('Faixa de preço criada!');
      }
      setDialogOpen(false);
      fetchPrecos();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao salvar faixa de preço.';
      toast.error(msg);
    }
  };

  const handleDeletePreco = async (id: string) => {
    if (!confirm('Deseja realmente excluir esta faixa de preço?')) return;
    try {
      await api.delete(`/config/precos-particulares/${id}`);
      toast.success('Faixa de preço excluída!');
      fetchPrecos();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao excluir faixa de preço.';
      toast.error(msg);
    }
  };

  if (!isGestorOrAdmin) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <p className="text-muted-foreground">Você não tem permissão para acessar esta página.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Tarifas de Corridas Particulares</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie as faixas horárias e os preços do KM/minuto para corridas particulares.
          </p>
        </div>
        <Button onClick={handleOpenCreate} className="flex items-center gap-2">
          <Plus size={16} /> Nova Faixa
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {loadingPrecos ? (
            <p className="text-sm text-muted-foreground">Carregando faixas horárias...</p>
          ) : precos.length === 0 ? (
            <div className="text-center py-12 space-y-3">
              <CurrencyDollar className="mx-auto text-muted-foreground/50" size={48} />
              <p className="text-sm text-muted-foreground">
                Nenhuma faixa horária cadastrada. O sistema utilizará os valores padrão (R$ 2,00/km + R$ 0,50/min).
              </p>
            </div>
          ) : (
            <div className="border rounded-md overflow-hidden bg-card">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Identificador / Nome</TableHead>
                    <TableHead>Hora de Início</TableHead>
                    <TableHead>Hora de Fim</TableHead>
                    <TableHead>Preço por Km</TableHead>
                    <TableHead>Preço por Minuto</TableHead>
                    <TableHead>Preço Mínimo</TableHead>
                    <TableHead className="w-[100px] text-right">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {precos.map((p) => (
                    <TableRow key={p._id}>
                      <TableCell className="font-medium text-foreground">{p.nome}</TableCell>
                      <TableCell className="text-muted-foreground">{p.hora_inicio}</TableCell>
                      <TableCell className="text-muted-foreground">{p.hora_fim}</TableCell>
                      <TableCell className="font-semibold text-emerald-500">R$ {p.preco_km.toFixed(2)}</TableCell>
                      <TableCell className="font-semibold text-emerald-500">R$ {p.preco_minuto.toFixed(2)}</TableCell>
                      <TableCell className="font-semibold text-emerald-500">R$ {(p.preco_minimo ?? 0.0).toFixed(2)}</TableCell>
                      <TableCell className="text-right flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleOpenEdit(p)}
                          title="Editar"
                        >
                          <PencilSimple size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeletePreco(p._id!)}
                          title="Excluir"
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash size={16} />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <form onSubmit={handleSavePreco}>
            <DialogHeader>
              <DialogTitle>
                {editingId ? 'Editar Faixa de Tarifa' : 'Nova Faixa de Tarifa'}
              </DialogTitle>
              <DialogDescription>
                Configure os parâmetros da faixa horária de preços.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="nome" className="text-right">
                  Nome
                </Label>
                <Input
                  id="nome"
                  required
                  value={precoForm.nome}
                  onChange={(e) => setPrecoForm({ ...precoForm, nome: e.target.value })}
                  placeholder="Ex: Horário de Pico"
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="hora_inicio" className="text-right">
                  Início
                </Label>
                <Input
                  id="hora_inicio"
                  type="time"
                  required
                  value={precoForm.hora_inicio}
                  onChange={(e) => setPrecoForm({ ...precoForm, hora_inicio: e.target.value })}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="hora_fim" className="text-right">
                  Fim
                </Label>
                <Input
                  id="hora_fim"
                  type="time"
                  required
                  value={precoForm.hora_fim}
                  onChange={(e) => setPrecoForm({ ...precoForm, hora_fim: e.target.value })}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="preco_km" className="text-right">
                  Preço/Km
                </Label>
                <Input
                  id="preco_km"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={precoForm.preco_km}
                  onChange={(e) => setPrecoForm({ ...precoForm, preco_km: parseFloat(e.target.value) })}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="preco_minuto" className="text-right">
                  Preço/Min
                </Label>
                <Input
                  id="preco_minuto"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={precoForm.preco_minuto}
                  onChange={(e) => setPrecoForm({ ...precoForm, preco_minuto: parseFloat(e.target.value) })}
                  className="col-span-3"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="preco_minimo" className="text-right">
                  Preço Mínimo
                </Label>
                <Input
                  id="preco_minimo"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  value={precoForm.preco_minimo}
                  onChange={(e) => setPrecoForm({ ...precoForm, preco_minimo: parseFloat(e.target.value) })}
                  className="col-span-3"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit">Salvar</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
