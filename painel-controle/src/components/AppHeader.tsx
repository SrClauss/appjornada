import { Bell, SignOut, DownloadSimple, List } from '@phosphor-icons/react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard } from '@/hooks/useDashboard';
import { useApkVersion } from '@/hooks/useApkVersion';

interface AppHeaderProps {
  onToggleMobileMenu?: () => void;
}

export function AppHeader({ onToggleMobileMenu }: AppHeaderProps) {
  const { user, logout } = useAuth();
  const { kpis } = useDashboard();
  const { versao, urlDownload, nomeArquivo } = useApkVersion();

  const initials = user?.nome
    ? user.nome.split(' ').map((n) => n[0]).join('').substring(0, 2).toUpperCase()
    : 'AD';

  const alertCount = kpis.totalAlertas;

  return (
    <header className="sticky top-0 z-40 h-16 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80 shadow-md px-4 md:px-6 flex items-center justify-between">
      {/* Botão de Menu Mobile */}
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-2 rounded-xl text-slate-300 hover:bg-slate-800/60 hover:text-white transition-colors"
            title="Abrir Menu"
          >
            <List size={24} />
          </button>
        )}
        <div className="md:hidden font-bold text-sm text-teal-400 tracking-wide">
          App Jornada
        </div>
      </div>

      <div className="flex items-center gap-3 md:gap-4">
        {/* Botão de Download do App Motorista APK Versionado */}
        <a
          href={urlDownload}
          download={nomeArquivo}
          className="flex items-center gap-1.5 md:gap-2 px-2.5 md:px-3 py-1.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all shadow-sm"
          title={`Baixar App Motorista Versão v${versao} (APK)`}
        >
          <DownloadSimple size={16} className="text-emerald-400" />
          <span className="hidden sm:inline">Baixar App v{versao} (APK)</span>
          <span className="sm:hidden">APK v{versao}</span>
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

        <div className="flex items-center gap-2 md:gap-3 pl-3 md:pl-4 border-l border-slate-800">
          <div className="text-right hidden sm:block">
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
