import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ShieldCheck, UserCheck, Lock, CheckCircle2, AlertTriangle, Loader2, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';

export const RegistroAdminView: React.FC = () => {
  const hash = window.location.hash;
  const token = new URLSearchParams(hash.includes('?') ? hash.split('?')[1] : '').get('token');

  const navigateTo = (path: string) => {
    window.location.hash = path.startsWith('/') ? path : `/${path}`;
  };

  const [loading, setLoading] = useState(true);
  const [conviteValido, setConviteValido] = useState(false);
  const [roleConvite, setRoleConvite] = useState<string>('ADMIN');
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);

  const [form, setForm] = useState({
    nome: '',
    email: '',
    senha: '',
    confirmacao_senha: '',
    pin: '',
  });

  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setMensagemErro('Link de convite inválido ou ausente.');
      return;
    }

    api
      .get(`/auth/convites/validar/${token}`)
      .then((res) => {
        if (res.data && res.data.valido) {
          setConviteValido(true);
          setRoleConvite(res.data.role || 'ADMIN');
        } else {
          setMensagemErro('Este convite não é mais válido.');
        }
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Erro ao validar o convite de cadastro.';
        setMensagemErro(msg);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!form.nome.trim() || !form.email.trim()) {
      toast.error('Preencha seu nome e e-mail.');
      return;
    }

    if (form.senha.length < 6) {
      toast.error('A senha deve conter no mínimo 6 caracteres.');
      return;
    }

    if (form.senha !== form.confirmacao_senha) {
      toast.error('As senhas não coincidem!');
      return;
    }

    if (roleConvite === 'MOTORISTA' && form.pin.length !== 4) {
      toast.error('O PIN do motorista deve ter exatamente 4 dígitos numéricos.');
      return;
    }

    setSubmitting(true);

    try {
      await api.post('/auth/convites/aceitar', {
        token,
        nome: form.nome,
        email: form.email,
        senha: form.senha,
        confirmacao_senha: form.confirmacao_senha,
        pin: roleConvite === 'MOTORISTA' ? form.pin : undefined,
      });

      toast.success(`🎉 Cadastro de ${roleConvite.toLowerCase()} realizado com sucesso!`);
      navigateTo('/login');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Erro ao registrar conta.';
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Elementos decorativos de fundo */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-primary/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300">
            <ShieldCheck size={14} className="text-primary" />
            <span>Sistema App Jornada</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Registro de Administrador</h1>
          <p className="text-xs text-slate-400">Conclua a criação da sua conta executiva por convite seguro.</p>
        </div>

        <Card className="bg-slate-900/90 border-slate-800 shadow-2xl backdrop-blur-md">
          {loading ? (
            <CardContent className="py-12 flex flex-col items-center justify-center space-y-4">
              <Loader2 size={32} className="animate-spin text-primary" />
              <p className="text-xs text-slate-400 font-medium">Validando convite de 24 horas...</p>
            </CardContent>
          ) : mensagemErro ? (
            <CardContent className="py-8 space-y-4 text-center">
              <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
                <AlertTriangle size={24} />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-white">Convite Inválido ou Expirado</h3>
                <p className="text-xs text-slate-400">{mensagemErro}</p>
              </div>
              <Button
                variant="outline"
                className="w-full border-slate-800 text-slate-300 hover:bg-slate-800 text-xs mt-2"
                onClick={() => navigateTo('/login')}
              >
                Voltar para o Login
              </Button>
            </CardContent>
          ) : (
            <>
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                    <UserCheck className="text-emerald-400" size={18} />
                    Dados de Acesso
                  </CardTitle>
                  <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-semibold text-[10px]">
                    Nível: {roleConvite}
                  </Badge>
                </div>
                <CardDescription className="text-xs text-slate-400">
                  Preencha as informações abaixo para definir sua senha de login.
                </CardDescription>
              </CardHeader>

              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <input type="text" name="username" value={form.email} autoComplete="username" hidden readOnly />

                  <div className="space-y-1.5">
                    <Label className="text-xs text-slate-300">Nome Completo</Label>
                    <Input
                      type="text"
                      placeholder="Ex: Carlos Silva"
                      value={form.nome}
                      onChange={(e) => setForm({ ...form, nome: e.target.value })}
                      required
                      className="bg-slate-950 border-slate-800 text-white text-xs"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-slate-300">E-mail Corporativo</Label>
                    <Input
                      type="email"
                      placeholder="seu.email@empresa.com"
                      value={form.email}
                      onChange={(e) => setForm({ ...form, email: e.target.value })}
                      required
                      className="bg-slate-950 border-slate-800 text-white text-xs"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-slate-300">Senha de Acesso</Label>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      placeholder="No mínimo 6 caracteres"
                      value={form.senha}
                      onChange={(e) => setForm({ ...form, senha: e.target.value })}
                      required
                      className="bg-slate-950 border-slate-800 text-white text-xs"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-slate-300">Confirmar Senha</Label>
                    <Input
                      type="password"
                      autoComplete="new-password"
                      placeholder="Repita a senha criada"
                      value={form.confirmacao_senha}
                      onChange={(e) => setForm({ ...form, confirmacao_senha: e.target.value })}
                      required
                      className="bg-slate-950 border-slate-800 text-white text-xs"
                    />
                    {form.confirmacao_senha.length > 0 && (
                      <p
                        className={`text-[11px] font-medium flex items-center gap-1 mt-1 ${
                          form.senha === form.confirmacao_senha ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {form.senha === form.confirmacao_senha ? (
                          <>
                            <CheckCircle2 size={12} /> As senhas coincidem
                          </>
                        ) : (
                          <>
                            <AlertTriangle size={12} /> As senhas não coincidem
                          </>
                        )}
                      </p>
                    )}
                  </div>

                  {roleConvite === 'MOTORISTA' && (
                    <div className="space-y-1.5 p-3 bg-slate-950/60 border border-slate-800 rounded-lg">
                      <Label className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
                        <Lock size={14} /> PIN de 4 Dígitos para Login no App Mobile
                      </Label>
                      <Input
                        type="text"
                        maxLength={4}
                        placeholder="Ex: 1234"
                        value={form.pin}
                        onChange={(e) => setForm({ ...form, pin: e.target.value.replace(/\D/g, '') })}
                        required
                        className="bg-slate-900 border-slate-700 text-center font-mono text-lg tracking-widest text-emerald-400 font-bold"
                      />
                      <p className="text-[10px] text-slate-400">Este PIN será usado para entrar no aplicativo do celular.</p>
                    </div>
                  )}

                  <Button
                    type="submit"
                    disabled={submitting || (form.confirmacao_senha.length > 0 && form.senha !== form.confirmacao_senha)}
                    className="w-full bg-primary hover:bg-primary/90 text-white font-bold text-xs gap-2 py-5 shadow-lg shadow-primary/20 mt-2"
                  >
                    {submitting ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        Criando conta...
                      </>
                    ) : (
                      <>
                        Concluir Cadastro de Administrador
                        <ArrowRight size={15} />
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </div>
  );
};
