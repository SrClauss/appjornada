import { useState } from 'react';
import { Card } from '@/components/ui/card';
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
import { Pencil, ClockCounterClockwise, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useVeiculos, useCreateVeiculo, useUpdateVeiculo } from '@/hooks/useVeiculos';
import type { Veiculo, VehicleStatus, CreateVeiculoPayload } from '@/lib/types';

export function VeiculosView() {
  const { data: veiculos = [], isLoading } = useVeiculos();
  const createMutation = useCreateVeiculo();
  const updateMutation = useUpdateVeiculo();

  const [openCreate, setOpenCreate] = useState(false);
  const [editVeiculo, setEditVeiculo] = useState<Veiculo | null>(null);

  const emptyCreate: CreateVeiculoPayload = {
    id: '', marca_modelo: '', ano_modelo: '', cor: '', situacao: 'RODANDO', km_atual: 0,
  };
  const [form, setForm] = useState<CreateVeiculoPayload>(emptyCreate);
  const [editForm, setEditForm] = useState<{
    marca_modelo: string; cor: string; km_atual: number; situacao: VehicleStatus;
  }>({ marca_modelo: '', cor: '', km_atual: 0, situacao: 'RODANDO' });

  const rodando  = veiculos.filter((v) => v.situacao === 'RODANDO').length;
  const manutencao = veiculos.filter((v) => v.situacao === 'MANUTENCAO').length;
  const inativos = veiculos.filter((v) => v.situacao === 'INATIVO').length;

  const statusBadgeVariant = (status: VehicleStatus) => {
    if (status === 'RODANDO') return 'default' as const;
    if (status === 'MANUTENCAO') return 'secondary' as const;
    return 'destructive' as const;
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createMutation.mutateAsync(form);
      toast.success('Veículo criado!');
      setOpenCreate(false);
      setForm(emptyCreate);
    } catch {
      toast.error('Erro ao criar veículo. Verifique se a placa já existe.');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editVeiculo) return;
    try {
      await updateMutation.mutateAsync({ placa: editVeiculo.id, payload: editForm });
      toast.success('Veículo atualizado!');
      setEditVeiculo(null);
    } catch {
      toast.error('Erro ao atualizar veículo.');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex gap-4 p-4 bg-muted/30 rounded-lg">
          <span className="text-sm font-medium">{rodando} rodando</span>
          <span className="text-sm font-medium text-warning">{manutencao} em manutenção</span>
          <span className="text-sm font-medium text-muted-foreground">{inativos} inativos</span>
        </div>
        <Button onClick={() => setOpenCreate(true)}>
          <Plus size={16} className="mr-1" /> Novo Veículo
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-56 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {veiculos.length === 0 ? (
            <p className="text-muted-foreground col-span-3 text-center py-12">
              Nenhum veículo cadastrado.
            </p>
          ) : (
            veiculos.map((vehicle) => (
              <Card key={vehicle.id} className="p-4 hover:shadow-md transition-shadow">
                <div className="aspect-video rounded-lg mb-3 overflow-hidden bg-muted">
                  {vehicle.imagem_clrv_url ? (
                    <img
                      src={vehicle.imagem_clrv_url}
                      alt={vehicle.marca_modelo}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-4xl">
                      🚗
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-lg">{vehicle.id}</p>
                      <p className="text-sm text-muted-foreground">{vehicle.marca_modelo} • {vehicle.ano_modelo}</p>
                    </div>
                    <Badge variant={statusBadgeVariant(vehicle.situacao)}>{vehicle.situacao}</Badge>
                  </div>
                  <div className="text-sm space-y-1">
                    <p><span className="text-muted-foreground">Cor:</span> {vehicle.cor}</p>
                    <p><span className="text-muted-foreground">Km:</span> {vehicle.km_atual.toLocaleString('pt-BR')}</p>
                    {vehicle.vencimento_ipva && (
                      <p>
                        <span className="text-muted-foreground">IPVA:</span>{' '}
                        {new Date(vehicle.vencimento_ipva).toLocaleDateString('pt-BR')}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => {
                        setEditVeiculo(vehicle);
                        setEditForm({
                          marca_modelo: vehicle.marca_modelo,
                          cor: vehicle.cor,
                          km_atual: vehicle.km_atual,
                          situacao: vehicle.situacao,
                        });
                      }}
                    >
                      <Pencil size={16} className="mr-1" /> Editar
                    </Button>
                    <Button size="sm" variant="outline" className="flex-1">
                      <ClockCounterClockwise size={16} className="mr-1" /> Histórico
                    </Button>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      )}

      {/* Modal criar veículo */}
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>Novo Veículo</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label>Placa (ID)</Label>
              <Input
                required
                placeholder="TST1A23"
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value.toUpperCase() })}
              />
            </div>
            <div className="space-y-2">
              <Label>Marca / Modelo</Label>
              <Input
                required
                placeholder="HB20 Sense"
                value={form.marca_modelo}
                onChange={(e) => setForm({ ...form, marca_modelo: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Ano/Modelo</Label>
                <Input
                  placeholder="2023/2024"
                  value={form.ano_modelo}
                  onChange={(e) => setForm({ ...form, ano_modelo: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Cor</Label>
                <Input
                  placeholder="Prata"
                  value={form.cor}
                  onChange={(e) => setForm({ ...form, cor: e.target.value })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Km Atual</Label>
                <Input
                  type="number"
                  min={0}
                  value={form.km_atual}
                  onChange={(e) => setForm({ ...form, km_atual: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Situação</Label>
                <Select
                  value={form.situacao}
                  onValueChange={(v) => setForm({ ...form, situacao: v as VehicleStatus })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="RODANDO">RODANDO</SelectItem>
                    <SelectItem value="MANUTENCAO">MANUTENCAO</SelectItem>
                    <SelectItem value="INATIVO">INATIVO</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenCreate(false)}>Cancelar</Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Criando...' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal editar veículo */}
      <Dialog open={!!editVeiculo} onOpenChange={(o) => !o && setEditVeiculo(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Editar Veículo — {editVeiculo?.id}</DialogTitle></DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div className="space-y-2">
              <Label>Marca / Modelo</Label>
              <Input
                required
                value={editForm.marca_modelo}
                onChange={(e) => setEditForm({ ...editForm, marca_modelo: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Cor</Label>
                <Input
                  value={editForm.cor}
                  onChange={(e) => setEditForm({ ...editForm, cor: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Km Atual</Label>
                <Input
                  type="number"
                  min={0}
                  value={editForm.km_atual}
                  onChange={(e) => setEditForm({ ...editForm, km_atual: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Situação</Label>
              <Select
                value={editForm.situacao}
                onValueChange={(v) => setEditForm({ ...editForm, situacao: v as VehicleStatus })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="RODANDO">RODANDO</SelectItem>
                  <SelectItem value="MANUTENCAO">MANUTENCAO</SelectItem>
                  <SelectItem value="INATIVO">INATIVO</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditVeiculo(null)}>Cancelar</Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Salvando...' : 'Salvar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

