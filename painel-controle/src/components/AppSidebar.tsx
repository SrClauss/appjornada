import { 
  House, 
  Users, 
  Car, 
  ClipboardText, 
  Drop,
  Wrench, 
  Target, 
  Gear,
  SignOut,
  CurrencyDollar,
  Image,
  DownloadSimple,
  Gauge,
  Flame
} from '@phosphor-icons/react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

export interface NavItem {
  icon: React.ComponentType<{ className?: string; size?: number }>;
  label: string;
  id: string;
}

export const navItems: NavItem[] = [
  { icon: House, label: 'Dashboard', id: 'dashboard' },
  { icon: Gauge, label: 'Mapa Ao Vivo (Monitor)', id: 'monitor' },
  { icon: Flame, label: 'Mapa de Calor (Ticket)', id: 'mapa-calor' },
  { icon: Users, label: 'Motoristas', id: 'motoristas' },
  { icon: Car, label: 'Veículos', id: 'veiculos' },
  { icon: ClipboardText, label: 'Jornadas', id: 'jornadas' },
  { icon: Drop, label: 'Abastecimentos', id: 'abastecimentos' },
  { icon: Wrench, label: 'Manutenções', id: 'manutencoes' },
  { icon: Target, label: 'Metas & Bônus', id: 'metas' },
  { icon: CurrencyDollar, label: 'Tarifas Particulares', id: 'tarifas-particulares' },
  { icon: Image, label: 'Gestão de Mídias', id: 'gestao-midias' },
  { icon: Gear, label: 'Configurações', id: 'configuracoes' },
];

interface AppSidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
}

export function AppSidebar({ activeView, onNavigate }: AppSidebarProps) {
  const { logout, user } = useAuth();
  const showTarifas = user?.role === 'ADMIN' || user?.role === 'GESTOR';
  
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-slate-950/90 backdrop-blur-xl text-slate-100 flex flex-col border-r border-slate-800/80 shadow-2xl z-50">
      <div className="p-6 border-b border-slate-800/80 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-teal-400 flex items-center justify-center text-slate-950 font-black shadow-lg shadow-cyan-500/20">
          J
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">App Jornada</h1>
          <p className="text-[11px] text-teal-400 font-semibold tracking-wider uppercase">Fluent Fleet OS</p>
        </div>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {navItems
          .filter((item) => (item.id !== 'tarifas-particulares' && item.id !== 'gestao-midias') || showTarifas)
          .map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={cn(
                'w-full flex items-center gap-3.5 px-4 py-2.5 text-left rounded-xl transition-all duration-200 text-sm font-medium',
                'hover:bg-slate-800/60 hover:text-white',
                isActive && 'bg-teal-500/15 text-teal-300 border border-teal-500/30 font-semibold shadow-md shadow-teal-950/40'
              )}
            >
              <Icon size={20} className={cn('flex-shrink-0', isActive ? 'text-teal-400' : 'text-slate-400')} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-800/80 flex flex-col gap-2 bg-slate-950/50">
        <a
          href="/app-jornada-v1.0.7.apk"
          download="app-jornada-v1.0.7.apk"
          className="w-full flex items-center gap-3 px-3.5 py-2.5 text-left text-xs rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 font-semibold transition-all duration-200 border border-emerald-500/30 shadow-sm"
          title="Baixar App Motorista Versão v1.0.7 (APK)"
        >
          <DownloadSimple size={18} className="flex-shrink-0 text-emerald-400 animate-bounce" />
          <div className="flex flex-col">
            <span className="font-bold">Baixar App Motorista</span>
            <span className="text-[10px] text-emerald-400/80">v1.0.7 (APK)</span>
          </div>
        </a>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3.5 py-2 text-left text-xs rounded-xl hover:bg-red-500/15 text-slate-400 hover:text-red-300 transition-all duration-150"
        >
          <SignOut size={18} className="flex-shrink-0 text-slate-400" />
          <span>Sair do Sistema</span>
        </button>
        <div className="text-[10px] text-slate-500 px-1 mt-1 text-center font-mono">
          Fluent 2 • v1.0.7 • 2026
        </div>
      </div>
    </aside>
  );
}
