import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Gear, Shield, User, Bell, FileArrowUp } from '@phosphor-icons/react';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { useUpdateUser } from '@/hooks/useMotoristas';

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

  const [alertas, setAlertas] = useState({
    inatividade_gps: 30,
    vencimento_cnh: 30,
    vencimento_ipva: 60,
    km_revisao: 5000,
    email: true,
    sms: false,
    push: true,
  });

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

        {/* Alertas & Notificações */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="text-warning" size={24} />
              <CardTitle>Alertas & Notificações</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground font-medium">Limites de alerta</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Inatividade GPS (min)</Label>
                <Input
                  type="number"
                  value={alertas.inatividade_gps}
                  onChange={(e) => setAlertas({ ...alertas, inatividade_gps: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Venc. CNH (dias)</Label>
                <Input
                  type="number"
                  value={alertas.vencimento_cnh}
                  onChange={(e) => setAlertas({ ...alertas, vencimento_cnh: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Venc. IPVA (dias)</Label>
                <Input
                  type="number"
                  value={alertas.vencimento_ipva}
                  onChange={(e) => setAlertas({ ...alertas, vencimento_ipva: Number(e.target.value) })}
                />
              </div>
              <div className="space-y-2">
                <Label>Aviso Revisão (km)</Label>
                <Input
                  type="number"
                  value={alertas.km_revisao}
                  onChange={(e) => setAlertas({ ...alertas, km_revisao: Number(e.target.value) })}
                />
              </div>
            </div>
            <Separator />
            <p className="text-sm text-muted-foreground font-medium">Canais de notificação</p>
            <div className="space-y-3">
              {([
                { key: 'email', label: 'Notificações por E-mail' },
                { key: 'sms', label: 'Notificações por SMS' },
                { key: 'push', label: 'Notificações Push' },
              ] as const).map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between">
                  <Label htmlFor={`notif-${key}`} className="cursor-pointer">{label}</Label>
                  <Switch
                    id={`notif-${key}`}
                    checked={alertas[key]}
                    onCheckedChange={(v) => setAlertas({ ...alertas, [key]: v })}
                  />
                </div>
              ))}
            </div>
            <Button onClick={() => toast.success('Configurações de alertas salvas!')}>
              Salvar Alertas
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

        {/* Importação de Dados */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileArrowUp className="text-primary" size={24} />
              <CardTitle>Importação de Dados</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-medium mb-2">Formato esperado — Uber CSV</p>
                <div className="bg-muted rounded-lg p-3 text-xs font-mono text-muted-foreground space-y-1">
                  <p>data,corridas,km_total,faturamento,motorista</p>
                  <p>2024-01-15,8,142.5,350.00,João Silva</p>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Formato esperado — 99 CSV</p>
                <div className="bg-muted rounded-lg p-3 text-xs font-mono text-muted-foreground space-y-1">
                  <p>data,corridas,km_total,faturamento,motorista</p>
                  <p>2024-01-15,5,89.2,210.00,Maria Santos</p>
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Para importar arquivos CSV das plataformas, acesse a aba <strong>Relatórios → Importar CSV</strong>.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}


