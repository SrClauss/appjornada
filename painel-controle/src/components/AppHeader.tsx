import { Bell, SignOut, DownloadSimple } from '@phosphor-icons/react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard } from '@/hooks/useDashboard';

export function AppHeader() {
  const { user, logout } = useAuth();
  const { kpis } = useDashboard();

  const initials = user?.nome
    ? user.nome.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AD';

  const alertCount = kpis.totalAlertas;

  return (
    <header className="sticky top-0 z-40 h-16 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 shadow-md">
      <div className="h-full px-6 flex items-center justify-end gap-4">
        {/* Botão de Download do App Motorista APK Versionado */}
        <a
          href="/app-jornada-v1.0.8.apk"
          download="app-jornada-v1.0.8.apk"
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all shadow-sm"
          title="Baixar App Motorista Versão v1.0.8 (APK)"
        >
          <DownloadSimple size={16} className="text-emerald-400" />
          <span>Baixar App v1.0.8 (APK)</span>
        </a>
        
        <button className="relative p-2 hover:bg-slate-800/60 rounded-xl transition-colors text-slate-300">
          <Bell size={20} />
          {alertCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-[10px] font-bold bg-rose-500 text-white"
            >
              {alertCount}
            </Badge>
          )}
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
          <div className="text-right">
            <p className="text-sm font-semibold text-white">{user?.nome ?? 'Admin'}</p>
            <p className="text-[11px] text-teal-400 font-medium">{user?.role ?? 'ADMIN'}</p>
          </div>
          <Avatar className="h-9 w-9 border border-teal-500/30 shadow-md shadow-teal-950/50">
            <AvatarFallback className="bg-gradient-to-tr from-cyan-500 to-teal-400 text-slate-950 font-bold text-xs">
              {initials}
            </AvatarFallback>
          </Avatar>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl"
          onClick={logout}
          title="Sair"
        >
          <SignOut size={20} />
        </Button>
      </div>
    </header>
  );
}
