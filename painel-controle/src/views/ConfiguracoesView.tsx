import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Gear, Shield, User, Pencil, UserMinus, Plus, Timer } from '@phosphor-icons/react';
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

  const [inatividadeForm, setInatividadeForm] = useState({
    tempo_inatividade_minutos: 25,
    raio_mudanca_metros: 30,
    tempo_maximo_abastecimento_minutos: 30,
  });
  const [savingInatividade, setSavingInatividade] = useState(false);

  // IA & Token Management State
  const [saldoIa, setSaldoIa] = useState({
    saldo_inicial_brl: 150.0,
    saldo_atual_brl: 150.0,
    total_gasto_brl: 0.0,
    total_requisicoes: 0,
    total_tokens_entrada: 0,
    total_tokens_saida: 0,
  });
  const [precosIa, setPrecosIa] = useState({
    cotacao_usd_brl: 5.70,
    modelos: {
      'gemini-3.6-flash': { usd_input_1m: 0.075, usd_output_1m: 0.30 },
      'gemini-3.1-flash-lite': { usd_input_1m: 0.0375, usd_output_1m: 0.15 },
    }
  });
  const [loadingIa, setLoadingIa] = useState(false);
  const [openAjustarSaldo, setOpenAjustarSaldo] = useState(false);
  const [novoSaldoInput, setNovoSaldoInput] = useState('150.00');
  const [motivoSaldoInput, setMotivoSaldoInput] = useState('Recarga de Créditos Google Cloud');

  // Bases de Operações State
  const [bases, setBases] = useState<any[]>([]);
  const [loadingBases, setLoadingBases] = useState(false);
  const [openBaseDialog, setOpenBaseDialog] = useState(false);
  const [editingBase, setEditingBase] = useState<any | null>(null);

  const emptyBaseForm = {
    nome: '',
    cidade: 'São Mateus',
    estado: 'ES',
    lat: '-18.714392',
    lon: '-39.828049',
    zoom_padrao: 15,
    is_principal: false,
  };
  const [baseForm, setBaseForm] = useState(emptyBaseForm);

  const fetchBases = async () => {
    try {
      setLoadingBases(true);
      const res = await api.get('/config/bases');
      setBases(res.data || []);
    } catch (e) {
      console.error('Erro ao carregar bases:', e);
    } finally {
      setLoadingBases(false);
    }
  };

  const fetchIaData = async () => {
    try {
      setLoadingIa(true);
      const [resSaldo, resPrecos] = await Promise.all([
        api.get('/ocr/saldo-ia'),
        api.get('/ocr/precos-ia')
      ]);
      if (resSaldo.data) {
        setSaldoIa(resSaldo.data);
        setNovoSaldoInput(resSaldo.data.saldo_atual_brl.toString());
      }
      if (resPrecos.data) setPrecosIa(resPrecos.data);
    } catch (e) {
      console.error('Erro ao carregar dados de IA:', e);
    } finally {
      setLoadingIa(false);
    }
  };

  useEffect(() => {
    api.get('/config/inatividade')
      .then(res => {
        if (res.data) {
          setInatividadeForm({
            tempo_inatividade_minutos: res.data.tempo_inatividade_minutos ?? 25,
            raio_mudanca_metros: res.data.raio_mudanca_metros ?? 30,
            tempo_maximo_abastecimento_minutos: res.data.tempo_maximo_abastecimento_minutos ?? 30,
          });
        }
      })
      .catch(err => console.error('Erro ao carregar configurações de inatividade:', err));

    fetchBases();
    fetchIaData();
  }, []);

  const handleSaveSaldoIa = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const val = parseFloat(novoSaldoInput);
      if (isNaN(val)) return toast.error('Digite um valor numérico válido.');
      await api.post('/ocr/saldo-ia/ajustar', { novo_saldo_brl: val, motivo: motivoSaldoInput });
      toast.success('Saldo em R$ da IA atualizado com sucesso!');
      setOpenAjustarSaldo(false);
      fetchIaData();
    } catch (err) {
      toast.error('Erro ao ajustar saldo da IA.');
    }
  };

  const handleSavePrecosIa = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/ocr/precos-ia', precosIa);
      toast.success('Tabela de preços e cotação de IA atualizadas!');
      fetchIaData();
    } catch (err) {
      toast.error('Erro ao salvar preços de IA.');
    }
  };

  const handleSaveInatividade = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingInatividade(true);
    try {
      await api.put('/config/inatividade', inatividadeForm);
      toast.success('Parâmetros de inatividade salvos com sucesso!');
    } catch (err) {
      console.error(err);
      toast.error('Erro ao salvar parâmetros de inatividade.');
    } finally {
      setSavingInatividade(false);
    }
  };

  const handleSaveBase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        ...baseForm,
        lat: parseFloat(String(baseForm.lat)),
        lon: parseFloat(String(baseForm.lon)),
        zoom_padrao: Number(baseForm.zoom_padrao) || 15
      };
      if (editingBase?.id) {
        await api.put(`/config/bases/${editingBase.id}`, payload);
        toast.success('Base de operações atualizada com sucesso!');
      } else {
        await api.post('/config/bases', payload);
        toast.success('Base de operações cadastrada com sucesso!');
      }
      setOpenBaseDialog(false);
      setEditingBase(null);
      setBaseForm(emptyBaseForm);
      fetchBases();
    } catch (err) {
      toast.error('Erro ao salvar base de operações.');
    }
  };

  const handleDeleteBase = async (id: string) => {
    if (!confirm('Deseja realmente excluir esta base de operações?')) return;
    try {
      await api.delete(`/config/bases/${id}`);
      toast.success('Base de operações excluída.');
      fetchBases();
    } catch {
      toast.error('Erro ao excluir base.');
    }
  };

  const handleSetPrincipal = async (base: any) => {
    if (!base.id) return;
    try {
      await api.put(`/config/bases/${base.id}`, { ...base, is_principal: true });
      toast.success(`"${base.nome}" definida como Base Principal da frota!`);
      fetchBases();
    } catch {
      toast.error('Erro ao definir base principal.');
    }
  };

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
                  autoComplete="new-password"
                  placeholder="Digite a nova senha"
                  value={pwForm.nova}
                  onChange={(e) => setPwForm({ ...pwForm, nova: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Confirmar Nova Senha</Label>
                <Input
                  type="password"
                  autoComplete="new-password"
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

        {/* Configurações de Inatividade da Jornada */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Timer className="text-amber-500" size={24} />
              <CardTitle>Inatividade da Jornada</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveInatividade} className="space-y-4">
              <div className="space-y-2">
                <Label>Tempo Limite de Inatividade (minutos)</Label>
                <Input
                  type="number"
                  min={1}
                  value={inatividadeForm.tempo_inatividade_minutos}
                  onChange={(e) => setInatividadeForm({ ...inatividadeForm, tempo_inatividade_minutos: Number(e.target.value) })}
                />
                <p className="text-xs text-muted-foreground">Padrão: 25 minutos. Se o motorista permanecer sem deslocamento maior que o raio neste período, a jornada é pausada.</p>
              </div>

              <div className="space-y-2">
                <Label>Raio Mínimo de Deslocamento (metros)</Label>
                <Input
                  type="number"
                  step="0.1"
                  min={1}
                  value={inatividadeForm.raio_mudanca_metros}
                  onChange={(e) => setInatividadeForm({ ...inatividadeForm, raio_mudanca_metros: Number(e.target.value) })}
                />
                <p className="text-xs text-muted-foreground">Padrão: 30 metros. Movimentações iguais ou abaixo deste valor contam como inatividade acumulada.</p>
              </div>

              <div className="space-y-2">
                <Label>Tempo Máximo de Abastecimento (minutos)</Label>
                <Input
                  type="number"
                  min={1}
                  value={inatividadeForm.tempo_maximo_abastecimento_minutos}
                  onChange={(e) => setInatividadeForm({ ...inatividadeForm, tempo_maximo_abastecimento_minutos: Number(e.target.value) })}
                />
                <p className="text-xs text-muted-foreground">Padrão: 30 minutos. Limite de tempo permitido para parada de abastecimento sem ser considerada inatividade indesejada.</p>
              </div>

              <Button type="submit" disabled={savingInatividade} className="w-full">
                {savingInatividade ? 'Salvando...' : 'Salvar Parâmetros de Inatividade'}
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

      {/* Gestão Financeira de IA & Créditos Google Cloud */}
      {(user?.role === 'ADMIN' || user?.role === 'GESTOR') && (
        <Card className="mt-6 border-emerald-500/30 bg-emerald-950/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🤖</span>
              <div>
                <CardTitle className="text-emerald-400">Créditos de IA & Tokens Google Cloud (Gemini)</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Acompanhe em tempo real a dedução de créditos (R$), tokens de Visão Computacional e ajuste as tarifas por modelo.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => setOpenAjustarSaldo(true)}
              className="bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1 font-semibold"
            >
              Recarregar / Ajustar Saldo (R$)
            </Button>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-background/60 p-4 rounded-xl border border-emerald-500/20 shadow-sm">
                <p className="text-xs text-muted-foreground font-medium">Saldo Disponível (R$)</p>
                <p className="text-2xl font-bold text-emerald-400 mt-1">R$ {saldoIa.saldo_atual_brl.toFixed(2).replace('.', ',')}</p>
                <p className="text-[10px] text-muted-foreground mt-1">Crédito inicial: R$ {saldoIa.saldo_inicial_brl.toFixed(2)}</p>
              </div>
              <div className="bg-background/60 p-4 rounded-xl border border-primary/20 shadow-sm">
                <p className="text-xs text-muted-foreground font-medium">Total Gasto em IA</p>
                <p className="text-2xl font-bold text-primary mt-1">R$ {saldoIa.total_gasto_brl.toFixed(4).replace('.', ',')}</p>
                <p className="text-[10px] text-muted-foreground mt-1">{saldoIa.total_requisicoes} leituras executadas</p>
              </div>
              <div className="bg-background/60 p-4 rounded-xl border border-primary/20 shadow-sm">
                <p className="text-xs text-muted-foreground font-medium">Tokens de Entrada (Prompt/Fotos)</p>
                <p className="text-xl font-bold text-foreground mt-1">{saldoIa.total_tokens_entrada.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground mt-1">Imagens de hodômetro e cupons</p>
              </div>
              <div className="bg-background/60 p-4 rounded-xl border border-primary/20 shadow-sm">
                <p className="text-xs text-muted-foreground font-medium">Tokens de Saída (Respostas IA)</p>
                <p className="text-xl font-bold text-foreground mt-1">{saldoIa.total_tokens_saida.toLocaleString()}</p>
                <p className="text-[10px] text-muted-foreground mt-1">JSON estruturados extraídos</p>
              </div>
            </div>

            {/* Ajuste de Tarifas dos Modelos Gemini */}
            <form onSubmit={handleSavePrecosIa} className="pt-2 border-t border-primary/10">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-foreground">Tarifas dos Modelos Gemini (USD por 1 Milhão de Tokens)</h4>
                <div className="flex items-center gap-2">
                  <Label className="text-xs text-muted-foreground">Cotação Dólar (R$):</Label>
                  <Input
                    type="number"
                    step="0.01"
                    className="w-24 h-8 text-xs font-bold"
                    value={precosIa.cotacao_usd_brl}
                    onChange={(e) => setPrecosIa({ ...precosIa, cotacao_usd_brl: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-muted/40 p-3 rounded-lg border text-xs space-y-2">
                  <p className="font-bold text-primary">gemini-3.6-flash (Visão de Alta Precisão)</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-[10px]">USD Input / 1M:</Label>
                      <Input
                        type="number"
                        step="0.001"
                        className="h-7 text-xs"
                        value={precosIa.modelos['gemini-3.6-flash']?.usd_input_1m ?? 0.075}
                        onChange={(e) => setPrecosIa({
                          ...precosIa,
                          modelos: {
                            ...precosIa.modelos,
                            'gemini-3.6-flash': { ...precosIa.modelos['gemini-3.6-flash'], usd_input_1m: parseFloat(e.target.value) || 0 }
                          }
                        })}
                      />
                    </div>
                    <div>
                      <Label className="text-[10px]">USD Output / 1M:</Label>
                      <Input
                        type="number"
                        step="0.001"
                        className="h-7 text-xs"
                        value={precosIa.modelos['gemini-3.6-flash']?.usd_output_1m ?? 0.30}
                        onChange={(e) => setPrecosIa({
                          ...precosIa,
                          modelos: {
                            ...precosIa.modelos,
                            'gemini-3.6-flash': { ...precosIa.modelos['gemini-3.6-flash'], usd_output_1m: parseFloat(e.target.value) || 0 }
                          }
                        })}
                      />
                    </div>
                  </div>
                </div>

                <div className="bg-muted/40 p-3 rounded-lg border text-xs space-y-2">
                  <p className="font-bold text-primary">gemini-3.1-flash-lite (Ultra Rápido / Baixo Custo)</p>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-[10px]">USD Input / 1M:</Label>
                      <Input
                        type="number"
                        step="0.001"
                        className="h-7 text-xs"
                        value={precosIa.modelos['gemini-3.1-flash-lite']?.usd_input_1m ?? 0.0375}
                        onChange={(e) => setPrecosIa({
                          ...precosIa,
                          modelos: {
                            ...precosIa.modelos,
                            'gemini-3.1-flash-lite': { ...precosIa.modelos['gemini-3.1-flash-lite'], usd_input_1m: parseFloat(e.target.value) || 0 }
                          }
                        })}
                      />
                    </div>
                    <div>
                      <Label className="text-[10px]">USD Output / 1M:</Label>
                      <Input
                        type="number"
                        step="0.001"
                        className="h-7 text-xs"
                        value={precosIa.modelos['gemini-3.1-flash-lite']?.usd_output_1m ?? 0.15}
                        onChange={(e) => setPrecosIa({
                          ...precosIa,
                          modelos: {
                            ...precosIa.modelos,
                            'gemini-3.1-flash-lite': { ...precosIa.modelos['gemini-3.1-flash-lite'], usd_output_1m: parseFloat(e.target.value) || 0 }
                          }
                        })}
                      />
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-3 flex justify-end">
                <Button type="submit" size="sm" variant="outline" className="text-xs">
                  Salvar Tarifas e Cotação
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Modal Ajustar Saldo IA */}
      <Dialog open={openAjustarSaldo} onOpenChange={setOpenAjustarSaldo}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Recarregar / Ajustar Crédito de IA (R$)</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveSaldoIa} className="space-y-4 py-2">
            <div>
              <Label>Novo Saldo Disponível (R$)</Label>
              <Input
                type="number"
                step="0.01"
                value={novoSaldoInput}
                onChange={(e) => setNovoSaldoInput(e.target.value)}
                placeholder="150.00"
                required
              />
            </div>
            <div>
              <Label>Motivo da Alteração / Observação</Label>
              <Input
                value={motivoSaldoInput}
                onChange={(e) => setMotivoSaldoInput(e.target.value)}
                placeholder="Recarga de Créditos Google Cloud"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setOpenAjustarSaldo(false)}>
                Cancelar
              </Button>
              <Button type="submit" className="bg-emerald-600 hover:bg-emerald-500 text-white">
                Confirmar Saldo
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Gestão de Bases de Operações (Garagens e Centrais) */}
      {(user?.role === 'ADMIN' || user?.role === 'GESTOR') && (
        <Card className="mt-6">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <div className="flex items-center gap-2">
              <span className="text-2xl">🏢</span>
              <div>
                <CardTitle>Bases de Operações e Garagens</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Configure os pontos centrais de operação da frota e a centralização do mapa ao vivo.
                </p>
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => {
                setEditingBase(null);
                setBaseForm(emptyBaseForm);
                setOpenBaseDialog(true);
              }}
              className="flex items-center gap-1 bg-sky-600 hover:bg-sky-500 text-white"
            >
              <Plus size={16} /> Nova Base de Operações
            </Button>
          </CardHeader>
          <CardContent>
            {loadingBases ? (
              <p className="text-sm text-muted-foreground">Carregando bases...</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Base de Operações</TableHead>
                    <TableHead>Cidade / Estado</TableHead>
                    <TableHead>Coordenadas (Lat, Lon)</TableHead>
                    <TableHead>Zoom Padrão</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-[140px]">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bases.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                        Nenhuma base de operações cadastrada.
                      </TableCell>
                    </TableRow>
                  ) : (
                    bases.map((base) => (
                      <TableRow key={base.id}>
                        <TableCell className="font-medium flex items-center gap-2">
                          <span>🏢</span> {base.nome}
                        </TableCell>
                        <TableCell>{base.cidade || '—'} {base.estado ? `/ ${base.estado}` : ''}</TableCell>
                        <TableCell className="font-mono text-xs text-slate-600">
                          {typeof base.lat === 'number' ? base.lat.toFixed(8) : base.lat}, {typeof base.lon === 'number' ? base.lon.toFixed(8) : base.lon}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{base.zoom_padrao ?? 13}x</TableCell>
                        <TableCell>
                          {base.is_principal ? (
                            <Badge className="bg-sky-600 text-white font-bold">★ Base Principal</Badge>
                          ) : (
                            <Badge variant="outline" className="text-slate-500">Secundária</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            {!base.is_principal && (
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-[11px] px-2"
                                onClick={() => handleSetPrincipal(base)}
                                title="Definir como Base Principal"
                              >
                                Tornar Principal
                              </Button>
                            )}
                            <Button
                              size="icon"
                              variant="ghost"
                              title="Editar"
                              className="h-8 w-8"
                              onClick={() => {
                                setEditingBase(base);
                                setBaseForm({
                                  nome: base.nome,
                                  cidade: base.cidade || '',
                                  estado: base.estado || 'ES',
                                  lat: String(base.lat ?? ''),
                                  lon: String(base.lon ?? ''),
                                  zoom_padrao: base.zoom_padrao ?? 13,
                                  is_principal: !!base.is_principal,
                                });
                                setOpenBaseDialog(true);
                              }}
                            >
                              <Pencil size={16} />
                            </Button>
                            <Button
                              size="icon"
                              variant="ghost"
                              title="Excluir"
                              className="h-8 w-8 text-destructive"
                              onClick={() => handleDeleteBase(base.id)}
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

      {/* Modal Cadastro/Edição Base de Operações */}
      <Dialog open={openBaseDialog} onOpenChange={setOpenBaseDialog}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>{editingBase ? 'Editar Base de Operações' : 'Nova Base de Operações'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveBase} className="space-y-4">
            <div className="space-y-2">
              <Label>Nome da Base / Garagem *</Label>
              <Input
                required
                placeholder="Ex: Base Operacional São Mateus"
                value={baseForm.nome}
                onChange={(e) => setBaseForm({ ...baseForm, nome: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Cidade</Label>
                <Input
                  placeholder="São Mateus"
                  value={baseForm.cidade}
                  onChange={(e) => setBaseForm({ ...baseForm, cidade: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Estado (UF)</Label>
                <Input
                  placeholder="ES"
                  maxLength={2}
                  value={baseForm.estado}
                  onChange={(e) => setBaseForm({ ...baseForm, estado: e.target.value.toUpperCase() })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Latitude *</Label>
                <Input
                  required
                  type="text"
                  placeholder="-18.714392"
                  value={baseForm.lat}
                  onChange={(e) => setBaseForm({ ...baseForm, lat: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Longitude *</Label>
                <Input
                  required
                  type="text"
                  placeholder="-39.828049"
                  value={baseForm.lon}
                  onChange={(e) => setBaseForm({ ...baseForm, lon: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>Zoom Padrão (1 a 18)</Label>
                <Input
                  type="number"
                  min={1}
                  max={18}
                  value={baseForm.zoom_padrao}
                  onChange={(e) => setBaseForm({ ...baseForm, zoom_padrao: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2 flex flex-col justify-end">
                <label className="flex items-center gap-2 text-sm font-medium cursor-pointer pb-2">
                  <input
                    type="checkbox"
                    checked={baseForm.is_principal}
                    onChange={(e) => setBaseForm({ ...baseForm, is_principal: e.target.checked })}
                    className="w-4 h-4 text-sky-600 rounded"
                  />
                  <span>Base Principal da Frota</span>
                </label>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpenBaseDialog(false)}>
                Cancelar
              </Button>
              <Button type="submit">
                {editingBase ? 'Atualizar Base' : 'Cadastrar Base'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

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
