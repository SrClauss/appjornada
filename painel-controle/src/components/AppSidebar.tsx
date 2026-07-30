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
  Gauge
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
    <aside className="fixed left-0 top-0 h-screen w-64 bg-primary text-primary-foreground flex flex-col shadow-xl z-50">
      <div className="p-6 border-b border-primary-foreground/10">
        <h1 className="text-xl font-semibold tracking-tight">App Jornada</h1>
        <p className="text-xs text-primary-foreground/70 mt-1">Painel de Gestão</p>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4">
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
                'w-full flex items-center gap-3 px-6 py-3 text-left transition-all duration-150',
                'hover:bg-primary-foreground/10',
                isActive && 'bg-accent text-accent-foreground border-l-4 border-accent-foreground font-medium'
              )}
            >
              <Icon size={20} className="flex-shrink-0" />
              <span className="text-sm">{item.label}</span>
            </button>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-primary-foreground/10 flex flex-col gap-2">
        <a
          href="/app-release.apk"
          download="app-release.apk"
          className="w-full flex items-center gap-3 px-3 py-2 text-left text-sm rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 font-semibold transition-all duration-150 border border-emerald-500/30 shadow-sm"
        >
          <DownloadSimple size={20} className="flex-shrink-0 text-emerald-400" />
          <span>Baixar App Motorista</span>
        </a>
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 text-left text-sm rounded-lg hover:bg-red-500/20 text-red-200 hover:text-white transition-all duration-155"
        >
          <SignOut size={20} className="flex-shrink-0" />
          <span>Sair do Sistema</span>
        </button>
        <div className="text-xs text-primary-foreground/60 mt-1">
          v1.0.3 • 2026
        </div>
      </div>
    </aside>
  );
}
