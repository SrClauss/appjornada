import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pencil, ClockCounterClockwise, Plus, Image, Trash } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useVeiculos, useCreateVeiculo, useUpdateVeiculo, useDeleteVeiculo } from '@/hooks/useVeiculos';
import type { Veiculo, VehicleStatus, CreateVeiculoPayload, Jornada } from '@/lib/types';
import api from '@/lib/api';

export function VeiculosView() {
  const { data: veiculos = [], isLoading } = useVeiculos();
  const createMutation = useCreateVeiculo();
  const updateMutation = useUpdateVeiculo();
  const deleteMutation = useDeleteVeiculo();

  const [openCreate, setOpenCreate] = useState(false);
  const [editVeiculo, setEditVeiculo] = useState<Veiculo | null>(null);
  const [historyVeiculo, setHistoryVeiculo] = useState<Veiculo | null>(null);
  const [uploading, setUploading] = useState(false);

  const emptyCreate: CreateVeiculoPayload = {
    id: '', marca_modelo: '', ano_modelo: '', cor: '', situacao: 'RODANDO', km_atual: 0, foto_veiculo_url: '', custo_manutencao_por_km: 0, custo_depreciacao_por_km: 0
  };
  const [form, setForm] = useState<CreateVeiculoPayload>(emptyCreate);
  const [editForm, setEditForm] = useState<{
    marca_modelo: string; cor: string; km_atual: number; situacao: VehicleStatus;
    foto_veiculo_url?: string;
    custo_manutencao_por_km?: number;
    custo_depreciacao_por_km?: number;
  }>({ marca_modelo: '', cor: '', km_atual: 0, situacao: 'RODANDO', foto_veiculo_url: '', custo_manutencao_por_km: 0, custo_depreciacao_por_km: 0 });

  const handleUploadPhoto = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('arquivo', file);
      const { data } = await api.post<{ url: string }>('/uploads/veiculo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return data.url;
    } catch (err) {
      toast.error('Erro ao fazer upload da imagem.');
      return null;
    } finally {
      setUploading(false);
    }
  };

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
      const payload = {
        ...form,
        id_placa: form.id.trim().toUpperCase(),
        id: form.id.trim().toUpperCase(),
      };
      await createMutation.mutateAsync(payload as any);
      toast.success('Veículo criado com sucesso!');
      setOpenCreate(false);
      setForm(emptyCreate);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao criar veículo. Verifique se a placa já existe.';
      toast.error(msg);
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

  const handleDeleteVeiculo = async (vehicle: Veiculo) => {
    if (!confirm(`Deseja realmente EXCLUIR o veículo de placa ${vehicle.id} (${vehicle.marca_modelo})?`)) return;
    try {
      await deleteMutation.mutateAsync(vehicle.id);
      toast.success(`Veículo ${vehicle.id} excluído com sucesso!`);
    } catch {
      toast.error('Erro ao excluir veículo.');
    }
  };

  const { data: jornadasVeiculo = [] } = useQuery({
    queryKey: ['historico-jornadas-veiculo', historyVeiculo?.id],
    queryFn: async () => {
      if (!historyVeiculo) return [];
      const { data } = await api.get<Jornada[]>('/jornadas', {
        params: { veiculo_id: historyVeiculo.id, limit: 100 },
      });
      return data;
    },
    enabled: !!historyVeiculo,
  });

  const { data: manutencoesVeiculo = [] } = useQuery({
    queryKey: ['historico-manutencoes-veiculo', historyVeiculo?.id],
    queryFn: async () => {
      if (!historyVeiculo) return [];
      const { data } = await api.get<any[]>('/manutencoes', {
        params: { veiculo_id: historyVeiculo.id },
      });
      return data;
    },
    enabled: !!historyVeiculo,
  });

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
                <div className="aspect-video rounded-lg mb-3 overflow-hidden bg-muted flex items-center justify-center">
                  {vehicle.foto_veiculo_url ? (
                    <img
                      src={vehicle.foto_veiculo_url}
                      alt={vehicle.marca_modelo}
                      className="h-full w-full object-cover"
                    />
                  ) : vehicle.imagem_clrv_url ? (
                    <img
                      src={vehicle.imagem_clrv_url}
                      alt={vehicle.marca_modelo}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-4xl bg-slate-100">
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
                          foto_veiculo_url: vehicle.foto_veiculo_url,
                          custo_manutencao_por_km: vehicle.custo_manutencao_por_km,
                          custo_depreciacao_por_km: vehicle.custo_depreciacao_por_km,
                        });
                      }}
                    >
                      <Pencil size={16} className="mr-1" /> Editar
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => setHistoryVeiculo(vehicle)}
                    >
                      <ClockCounterClockwise size={16} className="mr-1" /> Histórico
                    </Button>

                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:bg-destructive/10 px-2"
                      title="Excluir Veículo"
                      onClick={() => handleDeleteVeiculo(vehicle)}
                    >
                      <Trash size={16} />
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
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Custo Manutenção / Km (R$)</Label>
                <Input
                  type="number" step="0.01" min={0}
                  value={form.custo_manutencao_por_km || 0}
                  onChange={(e) => setForm({ ...form, custo_manutencao_por_km: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Custo Depreciação / Km (R$)</Label>
                <Input
                  type="number" step="0.01" min={0}
                  value={form.custo_depreciacao_por_km || 0}
                  onChange={(e) => setForm({ ...form, custo_depreciacao_por_km: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Foto do Veículo</Label>
              <Input
                type="file"
                accept="image/*"
                disabled={uploading}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    const url = await handleUploadPhoto(file);
                    if (url) {
                      setForm({ ...form, foto_veiculo_url: url });
                      toast.success('Foto enviada com sucesso!');
                    }
                  }
                }}
              />
              {form.foto_veiculo_url && (
                <div className="text-xs text-green-600 flex items-center gap-1 font-semibold">
                  ✓ Foto anexada com sucesso
                </div>
              )}
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
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Custo Manutenção / Km (R$)</Label>
                <Input
                  type="number" step="0.01" min={0}
                  value={editForm.custo_manutencao_por_km || 0}
                  onChange={(e) => setEditForm({ ...editForm, custo_manutencao_por_km: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Custo Depreciação / Km (R$)</Label>
                <Input
                  type="number" step="0.01" min={0}
                  value={editForm.custo_depreciacao_por_km || 0}
                  onChange={(e) => setEditForm({ ...editForm, custo_depreciacao_por_km: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Foto do Veículo</Label>
              <Input
                type="file"
                accept="image/*"
                disabled={uploading}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    const url = await handleUploadPhoto(file);
                    if (url) {
                      setEditForm({ ...editForm, foto_veiculo_url: url });
                      toast.success('Foto enviada com sucesso!');
                    }
                  }
                }}
              />
              {editForm.foto_veiculo_url && (
                <div className="text-xs text-green-600 flex items-center gap-1 font-semibold">
                  ✓ Foto anexada com sucesso
                </div>
              )}
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

      {/* Modal Histórico Completo do Veículo */}
      <Dialog open={!!historyVeiculo} onOpenChange={(o) => !o && setHistoryVeiculo(null)}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl font-bold">
              <ClockCounterClockwise size={24} className="text-sky-500" />
              Histórico Completo — Veículo Placa {historyVeiculo?.id} ({historyVeiculo?.marca_modelo})
            </DialogTitle>
          </DialogHeader>

          {historyVeiculo && (
            <div className="space-y-6 pt-2">
              {/* Card Resumo do Veículo */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="p-3 bg-slate-900 text-white border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">KM Atual</span>
                  <span className="text-lg font-bold font-mono">{historyVeiculo.km_atual?.toLocaleString('pt-BR')} km</span>
                </Card>
                <Card className="p-3 bg-slate-900 text-white border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Jornadas Registradas</span>
                  <span className="text-lg font-bold font-mono">{jornadasVeiculo.length}</span>
                </Card>
                <Card className="p-3 bg-slate-900 text-white border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Total Manutenções</span>
                  <span className="text-lg font-bold font-mono">{manutencoesVeiculo.length}</span>
                </Card>
                <Card className="p-3 bg-slate-900 text-white border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-mono block">Faturamento Gerado</span>
                  <span className="text-lg font-bold font-mono text-emerald-400">
                    R$ {jornadasVeiculo.reduce((acc, j) => acc + (j.faturamento?.total_dia ?? 0), 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                </Card>
              </div>

              {/* Tabela de Jornadas do Veículo */}
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <span>🚗 Jornadas Realizadas ({jornadasVeiculo.length})</span>
                </h3>
                <div className="border rounded-xl overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>Data</TableHead>
                        <TableHead>Motorista</TableHead>
                        <TableHead>KM Inicial / Final</TableHead>
                        <TableHead>KM Rodados</TableHead>
                        <TableHead>Faturamento</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {jornadasVeiculo.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center py-6 text-slate-500 text-xs">
                            Nenhuma jornada registrada para este veículo.
                          </TableCell>
                        </TableRow>
                      ) : (
                        jornadasVeiculo.map((j) => (
                          <TableRow key={j.id}>
                            <TableCell className="font-mono text-xs font-semibold">{j.data}</TableCell>
                            <TableCell className="font-medium text-xs">{j.motorista_nome || j.motorista_id}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {j.km?.inicial ?? '—'} / {j.km?.final ?? '—'}
                            </TableCell>
                            <TableCell className="font-mono text-xs font-bold text-sky-600">
                              {j.km?.rodados ?? 0} km
                            </TableCell>
                            <TableCell className="font-mono text-xs font-bold text-emerald-600">
                              R$ {(j.faturamento?.total_dia ?? 0).toFixed(2)}
                            </TableCell>
                            <TableCell>
                              <Badge variant={j.status === 'ENCERRADA' ? 'outline' : 'default'}>
                                {j.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              {/* Tabela de Manutenções do Veículo */}
              <div className="space-y-3">
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <span>🔧 Histórico de Manutenções ({manutencoesVeiculo.length})</span>
                </h3>
                <div className="border rounded-xl overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow>
                        <TableHead>Entrada</TableHead>
                        <TableHead>Serviço / Oficina</TableHead>
                        <TableHead>KM na Entrada</TableHead>
                        <TableHead>Custo (R$)</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {manutencoesVeiculo.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="text-center py-6 text-slate-500 text-xs">
                            Nenhuma manutenção registrada para este veículo.
                          </TableCell>
                        </TableRow>
                      ) : (
                        manutencoesVeiculo.map((m) => (
                          <TableRow key={m.id || m._id}>
                            <TableCell className="font-mono text-xs">{m.entrada ? new Date(m.entrada).toLocaleDateString('pt-BR') : '—'}</TableCell>
                            <TableCell className="text-xs">
                              <span className="font-bold block">{m.servico}</span>
                              <span className="text-slate-500">{m.oficina}</span>
                            </TableCell>
                            <TableCell className="font-mono text-xs">{m.km ? `${m.km} km` : '—'}</TableCell>
                            <TableCell className="font-mono text-xs font-bold text-rose-600">
                              R$ {(m.custo ?? 0).toFixed(2)}
                            </TableCell>
                            <TableCell>
                              <Badge variant={m.status === 'CONCLUIDA' ? 'default' : 'secondary'}>
                                {m.status}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setHistoryVeiculo(null)}>
              Fechar Histórico
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

