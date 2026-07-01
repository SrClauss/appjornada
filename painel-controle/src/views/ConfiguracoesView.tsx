import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Gear, Shield, User, Pencil, UserMinus, Plus } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useUpdateUser, useAllUsers, useCreateMotorista, useDeleteUser } from '@/hooks/useMotoristas';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { User as UserType, Role, Situacao } from '@/lib/types';
import api from '@/lib/api';

export function ConfiguracoesView() {
  const { user } = useAuth();
  const updateMutation = useUpdateUser();

  const { data: allUsers = [], isLoading: isLoadingUsers } = useAllUsers();
  const createAdminMutation = useCreateMotorista();
  const deleteAdminMutation = useDeleteUser();

  const [openCreateAdmin, setOpenCreateAdmin] = useState(false);
  const [editAdmin, setEditAdmin] = useState<UserType | null>(null);

  const [adminForm, setAdminForm] = useState({
    nome: '',
    email: '',
    senha: '',
    role: 'GESTOR' as Role,
  });

  const [editAdminForm, setEditAdminForm] = useState({
    nome: '',
    role: 'GESTOR' as Role,
    situacao: 'Ativo' as Situacao,
  });

  const [profileForm, setProfileForm] = useState({
    nome: user?.nome ?? '',
    email: user?.email ?? '',
  });
  const [pwForm, setPwForm] = useState({ nova: '', confirmar: '' });

  const [metas, setMetas] = useState({
    horas_mensais: 220,
    horas_semanais: 44,
    horas_diarias: 8,
  });

  const [diasLimpeza, setDiasLimpeza] = useState(30);
  const [limparRawGps, setLimparRawGps] = useState(true);
  const [limparArquivosZip, setLimparArquivosZip] = useState(false);
  const [limparJornadasCompletas, setLimparJornadasCompletas] = useState(false);
  const [loadingLimpeza, setLoadingLimpeza] = useState(false);

  const handleCreateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await createAdminMutation.mutateAsync(adminForm);
      toast.success('Administrador/Gestor criado com sucesso!');
      setOpenCreateAdmin(false);
      setAdminForm({ nome: '', email: '', senha: '', role: 'GESTOR' });
    } catch {
      toast.error('Erro ao criar administrador/gestor.');
    }
  };

  const handleUpdateAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editAdmin) return;
    try {
      await updateMutation.mutateAsync({ id: editAdmin.id, payload: editAdminForm });
      toast.success('Administrador/Gestor atualizado!');
      setEditAdmin(null);
    } catch {
      toast.error('Erro ao atualizar administrador/gestor.');
    }
  };

  const handleDeleteAdmin = async (admin: UserType) => {
    if (!confirm(`Inativar administrador/gestor ${admin.nome}?`)) return;
    try {
      await deleteAdminMutation.mutateAsync(admin.id);
      toast.success('Administrador/Gestor inativado.');
    } catch {
      toast.error('Erro ao inativar administrador/gestor.');
    }
  };

  const handleExecutarLimpeza = async () => {
    if (!window.confirm(`Tem certeza de que deseja excluir dados anteriores a ${diasLimpeza} dias? Esta operação não pode ser desfeita.`)) {
      return;
    }
    
    setLoadingLimpeza(true);
    try {
      const response = await api.post('/jornadas/admin/limpar-dados-antigos', null, {
        params: {
          dias: diasLimpeza,
          limpar_raw_gps: limparRawGps,
          limpar_arquivos_zip: limparArquivosZip,
          limpar_jornadas_completas: limparJornadasCompletas
        }
      });
      const data = response.data;
      const itens = data.itens_deletados || {};
      
      let msg = 'Limpeza concluída com sucesso! ';
      if (itens.raw_gps !== undefined) msg += `Coordenadas: ${itens.raw_gps}. `;
      if (itens.arquivos_telemetria !== undefined) msg += `Arquivos de Rota: ${itens.arquivos_telemetria}. `;
      if (itens.jornadas !== undefined) msg += `Jornadas: ${itens.jornadas}.`;
      
      toast.success(msg);
    } catch (err) {
      console.error(err);
      toast.error('Erro ao executar limpeza administrativa.');
    } finally {
      setLoadingLimpeza(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    try {
      await updateMutation.mutateAsync({ id: user.id, payload: { nome: profileForm.nome } });
      toast.success('Perfil atualizado!');
    } catch {
      toast.error('Erro ao atualizar perfil.');
    }
  };

  const handleSavePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pwForm.nova !== pwForm.confirmar) {
      toast.error('As senhas não coincidem.');
      return;
    }
    if (!user) return;
    try {
      await updateMutation.mutateAsync({ id: user.id, payload: { senha: pwForm.nova } });
      toast.success('Senha alterada com sucesso!');
      setPwForm({ nova: '', confirmar: '' });
    } catch {
      toast.error('Erro ao alterar senha.');
    }
  };

  const adminsList = allUsers.filter(u => u.role === 'ADMIN' || u.role === 'GESTOR');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Configurações</h1>
        <p className="text-muted-foreground mt-1">Gerencie as configurações do sistema</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Perfil do usuário */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <User className="text-primary" size={24} />
              <CardTitle>Meu Perfil</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="space-y-2">
                <Label>Nome</Label>
                <Input
                  value={profileForm.nome}
                  onChange={(e) => setProfileForm({ ...profileForm, nome: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>E-mail</Label>
                <Input value={profileForm.email} disabled />
                <p className="text-xs text-muted-foreground">O e-mail não pode ser alterado.</p>
              </div>
              <div className="space-y-2">
                <Label>Função</Label>
                <Input value={user?.role ?? ''} disabled />
              </div>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? 'Salvando...' : 'Salvar Perfil'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Configurações Gerais (Metas CLT) */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Gear className="text-accent" size={24} />
              <CardTitle>Configurações Gerais</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Meta de Horas Mensais (CLT)</Label>
              <Input
                type="number"
                value={metas.horas_mensais}
                onChange={(e) => setMetas({ ...metas, horas_mensais: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label>Meta de Horas Semanais (CLT)</Label>
              <Input
                type="number"
                value={metas.horas_semanais}
                onChange={(e) => setMetas({ ...metas, horas_semanais: Number(e.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label>Meta de Horas Diárias (CLT)</Label>
              <Input
                type="number"
                value={metas.horas_diarias}
                onChange={(e) => setMetas({ ...metas, horas_diarias: Number(e.target.value) })}
              />
            </div>
            <Button onClick={() => toast.success('Configurações salvas!')}>
              Salvar Configurações
            </Button>
          </CardContent>
        </Card>

        {/* Segurança */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="text-success" size={24} />
              <CardTitle>Segurança</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSavePassword} className="space-y-4">
              <div className="space-y-2">
                <Label>Nova Senha</Label>
                <Input
                  type="password"
                  placeholder="Digite a nova senha"
                  value={pwForm.nova}
                  onChange={(e) => setPwForm({ ...pwForm, nova: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Confirmar Nova Senha</Label>
                <Input
                  type="password"
                  placeholder="Repita a nova senha"
                  value={pwForm.confirmar}
                  onChange={(e) => setPwForm({ ...pwForm, confirmar: e.target.value })}
                />
              </div>
              <Button
                type="submit"
                variant="outline"
                className="w-full"
                disabled={!pwForm.nova || pwForm.nova !== pwForm.confirmar || updateMutation.isPending}
              >
                Alterar Senha
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Gestão de Administradores/Gestores */}
      {(user?.role === 'ADMIN' || user?.role === 'GESTOR') && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-2">
              <Shield className="text-primary" size={24} />
              <CardTitle>Administradores e Gestores</CardTitle>
            </div>
            <Button size="sm" onClick={() => setOpenCreateAdmin(true)} className="flex items-center gap-1">
              <Plus size={16} /> Novo Administrador
            </Button>
          </CardHeader>
          <CardContent>
            {isLoadingUsers ? (
              <p className="text-sm text-muted-foreground">Carregando usuários...</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Nome</TableHead>
                    <TableHead>E-mail</TableHead>
                    <TableHead>Função</TableHead>
                    <TableHead>Situação</TableHead>
                    <TableHead className="w-[100px]">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {adminsList.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                        Nenhum administrador ou gestor encontrado.
                      </TableCell>
                    </TableRow>
                  ) : (
                    adminsList.map((admin) => (
                      <TableRow key={admin.id}>
                        <TableCell className="font-medium">{admin.nome}</TableCell>
                        <TableCell>{admin.email}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{admin.role}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={admin.situacao === 'Ativo' ? 'default' : 'destructive'}>
                            {admin.situacao}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1">
                            <Button
                              size="icon"
                              variant="ghost"
                              title="Editar"
                              className="h-8 w-8"
                              onClick={() => {
                                setEditAdmin(admin);
                                setEditAdminForm({
                                  nome: admin.nome,
                                  role: admin.role,
                                  situacao: admin.situacao,
                                });
                              }}
                            >
                              <Pencil size={16} />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              title="Inativar"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              onClick={() => handleDeleteAdmin(admin)}
                              disabled={admin.id === user?.id}
                            >
                              <UserMinus size={16} />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {user?.role === 'ADMIN' && (
        <Card className="border-red-900/20 bg-red-500/5 mt-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Shield className="text-red-500" size={24} />
              <CardTitle className="text-red-500">Limpeza Administrativa de Dados</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              Utilize esta ferramenta para purgar dados antigos do sistema e economizar espaço em disco e banco de dados. 
              <strong className="text-red-500 ml-1">Esta ação é irreversível.</strong>
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Manter dados dos últimos (dias)</Label>
                <Input 
                  type="number" 
                  value={diasLimpeza}
                  onChange={(e) => setDiasLimpeza(Number(e.target.value))}
                  min={1}
                />
              </div>
              
              <div className="space-y-3 pt-2">
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id="rawGps" 
                    checked={limparRawGps} 
                    onChange={(e) => setLimparRawGps(e.target.checked)}
                    className="rounded border-slate-350"
                  />
                  <Label htmlFor="rawGps" className="cursor-pointer text-xs">
                    Excluir coordenadas brutas do GPS do MongoDB (Recomendado)
                  </Label>
                </div>
                
                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id="archivedGps" 
                    checked={limparArquivosZip} 
                    onChange={(e) => setLimparArquivosZip(e.target.checked)}
                    className="rounded border-slate-350"
                  />
                  <Label htmlFor="archivedGps" className="cursor-pointer text-xs">
                    Excluir arquivos comprimidos (.json.gz) de rotas antigas no storage
                  </Label>
                </div>

                <div className="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id="fullJourneys" 
                    checked={limparJornadasCompletas} 
                    onChange={(e) => setLimparJornadasCompletas(e.target.checked)}
                    className="rounded border-slate-350"
                  />
                  <Label htmlFor="fullJourneys" className="cursor-pointer text-xs text-red-500 font-semibold">
                    Excluir jornadas e relatórios completamente do banco de dados
                  </Label>
                </div>
              </div>
            </div>

            <Button 
              variant="destructive"
              disabled={loadingLimpeza}
              onClick={handleExecutarLimpeza}
              className="w-full md:w-auto"
            >
              {loadingLimpeza ? 'Processando Limpeza...' : 'Executar Limpeza de Dados'}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Modal Criar Admin/Gestor */}
      <Dialog open={openCreateAdmin} onOpenChange={setOpenCreateAdmin}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo Administrador / Gestor</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateAdmin} className="space-y-4">
            <div className="space-y-2">
              <Label>Nome Completo</Label>
              <Input
                required
                value={adminForm.nome}
                onChange={(e) => setAdminForm({ ...adminForm, nome: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>E-mail</Label>
              <Input
                type="email"
                required
                value={adminForm.email}
                onChange={(e) => setAdminForm({ ...adminForm, email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Senha Inicial</Label>
              <Input
                type="password"
                required
                minLength={6}
                value={adminForm.senha}
                onChange={(e) => setAdminForm({ ...adminForm, senha: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Função</Label>
              <Select
                value={adminForm.role}
                onValueChange={(v) => setAdminForm({ ...adminForm, role: v as Role })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GESTOR">GESTOR</SelectItem>
                  <SelectItem value="ADMIN">ADMIN</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenCreateAdmin(false)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createAdminMutation.isPending}>
                {createAdminMutation.isPending ? 'Criando...' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Modal Editar Admin/Gestor */}
      <Dialog open={!!editAdmin} onOpenChange={(o) => !o && setEditAdmin(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar Administrador / Gestor</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleUpdateAdmin} className="space-y-4">
            <div className="space-y-2">
              <Label>Nome Completo</Label>
              <Input
                required
                value={editAdminForm.nome}
                onChange={(e) => setEditAdminForm({ ...editAdminForm, nome: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Função</Label>
              <Select
                value={editAdminForm.role}
                onValueChange={(v) => setEditAdminForm({ ...editAdminForm, role: v as Role })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GESTOR">GESTOR</SelectItem>
                  <SelectItem value="ADMIN">ADMIN</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Situação</Label>
              <Select
                value={editAdminForm.situacao}
                onValueChange={(v) => setEditAdminForm({ ...editAdminForm, situacao: v as Situacao })}
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
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditAdmin(null)}>
                Cancelar
              </Button>
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
