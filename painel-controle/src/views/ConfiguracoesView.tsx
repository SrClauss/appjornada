import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Gear, Shield, User } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useUpdateUser } from '@/hooks/useMotoristas';
import api from '@/lib/api';

export function ConfiguracoesView() {
  const { user } = useAuth();
  const updateMutation = useUpdateUser();

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
    </div>
  );
}
