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
import { Eye, Pencil, UserMinus, Trash } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useMotoristas, useCreateMotorista, useUpdateUser, useDeleteUser } from '@/hooks/useMotoristas';
import type { User, Role, Situacao } from '@/lib/types';

export function MotoristasView() {
  const [search, setSearch] = useState('');
  const [openCreate, setOpenCreate] = useState(false);
  const [editUser, setEditUser] = useState<User | null>(null);
  const [viewUser, setViewUser] = useState<User | null>(null);

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

  return (
    <div className="space-y-6">
      <div className="flex gap-4 items-center justify-between">
        <Input
          placeholder="Buscar por nome..."
          className="max-w-md"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Button onClick={() => setOpenCreate(true)}>+ Novo Motorista</Button>
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
                <TableHead>Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {motoristas.length === 0 ? (
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
    </div>
  );
}

