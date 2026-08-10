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
    <header className="sticky top-0 z-40 h-16 bg-card border-b border-border shadow-sm">
      <div className="h-full px-6 flex items-center justify-end gap-4">
        {/* Botão de Download do App Motorista APK Versionado */}
        <a
          href="/app-jornada-v1.0.4.apk"
          download="app-jornada-v1.0.4.apk"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-xs font-bold transition-all shadow-sm"
          title="Baixar App Motorista Versão v1.0.4 (APK)"
        >
          <DownloadSimple size={16} className="text-emerald-500" />
          <span>Baixar App v1.0.4 (APK)</span>
        </a>
        <button className="relative p-2 hover:bg-muted rounded-lg transition-colors">
          <Bell size={20} className="text-foreground" />
          {alertCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
            >
              {alertCount}
            </Badge>
          )}
        </button>

        <div className="flex items-center gap-3 pl-4 border-l border-border">
          <div className="text-right">
            <p className="text-sm font-medium text-foreground">{user?.nome ?? 'Admin'}</p>
            <p className="text-xs text-muted-foreground">{user?.role ?? 'ADMIN'}</p>
          </div>
          <Avatar>
            <AvatarFallback className="bg-accent text-accent-foreground font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:text-destructive"
          onClick={logout}
          title="Sair"
        >
          <SignOut size={20} />
        </Button>
      </div>
    </header>
  );
}
