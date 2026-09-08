import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { useQuery } from '@tanstack/react-query';
import { Eye, Pencil, UserMinus, Trash, LockKeyOpen, ShieldWarning, CheckCircle } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useMotoristas, useCreateMotorista, useUpdateUser, useDeleteUser } from '@/hooks/useMotoristas';
import type { User, Role, Situacao, Jornada } from '@/lib/types';
import api from '@/lib/api';
import { ConviteModal } from '@/components/ConviteModal';
import { QrCode } from 'lucide-react';

export function MotoristasView() {
  const [search, setSearch] = useState('');
  const [openCreate, setOpenCreate] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [viewUser, setViewUser] = useState<User | null>(null);

  const [conviteModalOpen, setConviteModalOpen] = useState(false);
  const [inviteData, setInviteData] = useState<{
    token: string;
    invite_url: string;
    role: string;
    expira_em: string;
  } | null>(null);
  const [gerandoConvite, setGerandoConvite] = useState(false);
  const [liberandoId, setLiberandoId] = useState<string | null>(null);
  const [filtroPendentes, setFiltroPendentes] = useState(false);

  const { data: jornadasPendentes = [], refetch: refetchPendentes } = useQuery({
    queryKey: ['jornadas-pendentes-lista'],
    queryFn: async () => {
      const res = await api.get<Jornada[]>('/jornadas', { params: { limit: 200 } });
      const items = res.data || [];
      return items.filter((j) => j.auditoria_status === 'PENDENTE');
    },
    staleTime: 10000,
  });

  const handleLiberarJornada = async (jornadaId: string, motoristaNome: string) => {
    setLiberandoId(jornadaId);
    try {
      await api.post(`/jornadas/${jornadaId}/auditoria/aprovar`);
      toast.success(`Jornada de ${motoristaNome} liberada com sucesso!`);
      refetchPendentes();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Erro ao liberar jornada.');
    } finally {
      setLiberandoId(null);
    }
  };

  const handleGerarConviteMotorista = async () => {
    setGerandoConvite(true);
    try {
      const res = await api.post('/auth/convites/gerar', { role: 'MOTORISTA' });
      setInviteData(res.data);
      setConviteModalOpen(true);
      toast.success('Convite de Motorista gerado com sucesso!');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Erro ao gerar convite.');
    } finally {
      setGerandoConvite(false);
    }
  };

  const { data: motoristas = [], isLoading } = useMotoristas(search);
  const createMutation = useCreateMotorista();
  const updateMutation = useUpdateUser();
  const deleteMutation = useDeleteUser();

  const [form, setForm] = useState({ nome: '', email: '', senha: '', pin: '', role: 'MOTORISTA' as Role });
  const [editForm, setEditForm] = useState({ nome: '', situacao: 'Ativo' as Situacao, pin: '' });

  const getInitials = (nome: string) =>
    nome.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        senha: form.role !== 'MOTORISTA' ? form.senha : undefined,
        pin: form.role === 'MOTORISTA' && form.pin ? form.pin : undefined,
      };
      await createMutation.mutateAsync(payload);
      toast.success('Motorista criado com sucesso!');
      setOpenCreate(false);
      setForm({ nome: '', email: '', senha: '', pin: '', role: 'MOTORISTA' });
    } catch {
      toast.error('Erro ao criar motorista.');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editUser) return;
    try {
      const payload = {
        ...editForm,
        pin: editForm.pin ? editForm.pin : undefined,
      };
      await updateMutation.mutateAsync({ id: editUser.id, payload });
      toast.success('Motorista atualizado!');
      setEditUser(null);
    } catch {
      toast.error('Erro ao atualizar motorista.');
    }
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Inativar ${user.nome}?`)) return;
    try {
      await deleteMutation.mutateAsync(user.id);
      toast.success('Motorista inativado.');
    } catch {
      toast.error('Erro ao inativar motorista.');
    }
  };

  const handleHardDelete = async (user: User) => {
    if (!confirm(`Excluir permanentemente o motorista ${user.nome}? Esta ação não pode ser desfeita.`)) return;
    try {
      await deleteMutation.mutateAsync({ id: user.id, hard: true });
      toast.success('Motorista excluído com sucesso.');
    } catch {
      toast.error('Erro ao excluir motorista.');
    }
  };

  const filteredMotoristas = motoristas.filter((d) => {
    if (!filtroPendentes) return true;
    return jornadasPendentes.some((j) => String(j.motorista_id) === String(d.id) || j.motorista_nome === d.nome);
  });

  return (
    <div className="space-y-6">
      {jornadasPendentes.length > 0 && (
        <Card className="bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-slate-900 border-amber-500/40 p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-500/20 border border-amber-500/30 rounded-xl text-amber-400">
              <ShieldWarning size={24} />
            </div>
            <div>
              <h4 className="text-sm font-bold text-amber-200">
                {jornadasPendentes.length} {jornadasPendentes.length === 1 ? 'Motorista com Jornada Pendente' : 'Motoristas com Jornadas Pendentes'}
              </h4>
              <p className="text-xs text-amber-300/80">
                Há jornadas aguardando liberação para que os motoristas possam iniciar novos trabalhos.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setFiltroPendentes(!filtroPendentes)}
              className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20 text-xs font-semibold"
            >
              {filtroPendentes ? 'Ver Todos os Motoristas' : 'Filtrar Somente Pendentes'}
            </Button>
          </div>
        </Card>
      )}
      <div className="flex gap-4 items-center justify-between">
        <Input
          placeholder="Buscar por nome..."
          className="max-w-md"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleGerarConviteMotorista}
            disabled={gerandoConvite}
            className="flex items-center gap-1.5 border-primary/40 text-primary hover:bg-primary/10 font-semibold"
          >
            <QrCode size={16} />
            {gerandoConvite ? 'Gerando...' : 'Gerar Convite (QR Code 24h)'}
          </Button>
          <Button onClick={() => setOpenCreate(true)}>+ Novo Motorista Direto</Button>
        </div>
      </div>

      <Card className="p-6">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Motorista</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>PIN</TableHead>
                <TableHead>Situação</TableHead>
                <TableHead>Status Auditoria</TableHead>
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredMotoristas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                    Nenhum motorista encontrado.
                  </TableCell>
                </TableRow>
              ) : (
                motoristas.map((driver) => (
                  <TableRow key={driver.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar>
                          <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                            {getInitials(driver.nome)}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-medium">{driver.nome}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{driver.email}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{driver.role}</Badge>
                    </TableCell>
                    <TableCell>
                      {driver.role === 'MOTORISTA' ? (
                        driver.has_pin ? (
                          <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900/50">
                            Sim
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-900/50">
                            Não
                          </Badge>
                        )
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={driver.situacao === 'Ativo' ? 'default' : 'destructive'}>
                        {driver.situacao}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {(() => {
                        const pendente = jornadasPendentes.find(
                          (j) => String(j.motorista_id) === String(driver.id) || j.motorista_nome === driver.nome
                        );
                        if (pendente) {
                          return (
                            <div className="flex items-center gap-2">
                              <Badge className="bg-amber-500/15 text-amber-500 border-amber-500/30 flex items-center gap-1 font-bold">
                                <ShieldWarning size={14} className="text-amber-500" />
                                Pendente
                              </Badge>
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={liberandoId === pendente.id}
                                onClick={() => handleLiberarJornada(pendente.id, driver.nome)}
                                className="border-amber-500/40 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 font-semibold text-xs gap-1.5 h-8 px-2.5"
                                title="Liberar motorista aprovando a auditoria da jornada"
                              >
                                <LockKeyOpen size={14} />
                                {liberandoId === pendente.id ? 'Liberando...' : 'Liberar'}
                              </Button>
                            </div>
                          );
                        }
                        return (
                          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/30 flex items-center gap-1 w-fit text-xs">
                            <CheckCircle size={12} />
                            Liberado
                          </Badge>
                        );
                      })()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Ver detalhes"
                          onClick={() => setViewUser(driver)}
                        >
                          <Eye size={16} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Editar"
                          onClick={() => {
                            setEditUser(driver);
                            setEditForm({ nome: driver.nome, situacao: driver.situacao, pin: '' });
                          }}
                        >
                          <Pencil size={16} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Inativar"
                          onClick={() => handleDelete(driver)}
                        >
                          <UserMinus size={16} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          title="Excluir permanentemente"
                          onClick={() => handleHardDelete(driver)}
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        >
                          <Trash size={16} />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Modal criar motorista */}
      <Dialog open={openCreate} onOpenChange={setOpenCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo Motorista</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-2">
              <Label>Nome completo</Label>
              <Input
                required
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>E-mail</Label>
              <Input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            {form.role !== 'MOTORISTA' && (
              <div className="space-y-2">
                <Label>Senha inicial</Label>
                <Input
                  type="password"
                  required
                  minLength={6}
                  value={form.senha}
                  onChange={(e) => setForm({ ...form, senha: e.target.value })}
                />
              </div>
            )}
            <div className="space-y-2">
              <Label>Role</Label>
              <Select
                value={form.role}
                onValueChange={(v) => setForm({ ...form, role: v as Role })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MOTORISTA">MOTORISTA</SelectItem>
                  <SelectItem value="GESTOR">GESTOR</SelectItem>
                  <SelectItem value="ADMIN">ADMIN</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.role === 'MOTORISTA' && (
              <div className="space-y-2">
                <Label>PIN de Jornada (4 dígitos)</Label>
                <Input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{4}"
                  maxLength={4}
                  required
                  placeholder="Ex: 1234"
                  value={form.pin}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '');
                    setForm({ ...form, pin: val });
                  }}
                />
              </div>
            )}
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

      {/* Modal editar motorista */}
      <Dialog open={!!editUser} onOpenChange={(o) => !o && setEditUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Motorista</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-4">
            <div className="space-y-2">
              <Label>Nome</Label>
              <Input
                required
                value={editForm.nome}
                onChange={(e) => setEditForm({ ...editForm, nome: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Situação</Label>
              <Select
                value={editForm.situacao}
                onValueChange={(v) => setEditForm({ ...editForm, situacao: v as Situacao })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Ativo">Ativo</SelectItem>
                  <SelectItem value="Inativo">Inativo</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {editUser?.role === 'MOTORISTA' && (
              <div className="space-y-2">
                <Label>Novo PIN de Jornada (4 dígitos - opcional)</Label>
                <Input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{4}"
                  maxLength={4}
                  placeholder={editUser.has_pin ? "•••• (PIN cadastrado)" : "Cadastrar novo PIN"}
                  value={editForm.pin}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '');
                    setEditForm({ ...editForm, pin: val });
                  }}
                />
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditUser(null)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Salvando...' : 'Salvar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal visualizar motorista */}
      <Dialog open={!!viewUser} onOpenChange={(open) => !open && setViewUser(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Detalhes do Motorista</DialogTitle>
            <DialogDescription>
              Informações completas do perfil do motorista.
            </DialogDescription>
          </DialogHeader>
          {viewUser ? (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <Avatar>
                  <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                    {getInitials(viewUser.nome)}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-lg font-semibold">{viewUser.nome}</p>
                  <p className="text-sm text-muted-foreground">{viewUser.email}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Role</p>
                  <p className="font-medium">{viewUser.role}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Situação</p>
                  <Badge variant={viewUser.situacao === 'Ativo' ? 'default' : 'destructive'}>
                    {viewUser.situacao}
                  </Badge>
                </div>
                {viewUser.role === 'MOTORISTA' && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">PIN de Jornada</p>
                    <Badge variant={viewUser.has_pin ? 'outline' : 'secondary'} className={viewUser.has_pin ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900/50" : ""}>
                      {viewUser.has_pin ? 'Cadastrado' : 'Não cadastrado'}
                    </Badge>
                  </div>
                )}
              </div>

              {viewUser.perfil_motorista && (
                <div className="space-y-4 pt-4 border-t border-muted/60">
                  <p className="font-semibold">Perfil do Motorista</p>
                  {viewUser.perfil_motorista.telefone && (
                    <p>
                      <span className="text-muted-foreground">Telefone:</span>{' '}
                      {viewUser.perfil_motorista.telefone}
                    </p>
                  )}
                  {viewUser.perfil_motorista.cpf && (
                    <p>
                      <span className="text-muted-foreground">CPF:</span>{' '}
                      {viewUser.perfil_motorista.cpf}
                    </p>
                  )}
                  {viewUser.perfil_motorista.cnh?.vencimento && (
                    <p>
                      <span className="text-muted-foreground">CNH vence em:</span>{' '}
                      {new Date(viewUser.perfil_motorista.cnh.vencimento).toLocaleDateString('pt-BR')}
                    </p>
                  )}
                </div>
              )}

              <DialogFooter>
                <Button type="button" onClick={() => setViewUser(null)}>
                  Fechar
                </Button>
              </DialogFooter>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      <ConviteModal
        open={conviteModalOpen}
        onOpenChange={setConviteModalOpen}
        inviteData={inviteData}
      />
    </div>
  );
}

