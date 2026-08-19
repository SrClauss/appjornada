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
  Flame,
  X
} from '@phosphor-icons/react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

export interface NavItem {
  icon: React.ComponentType<{ className?: string; size?: number }>;
  label: string;
  id: string;
  category?: string;
}

export const navItems: NavItem[] = [
  { icon: House, label: 'Dashboard', id: 'dashboard', category: 'OPERAÇÃO' },
  { icon: Gauge, label: 'Mapa Ao Vivo (Monitor)', id: 'monitor', category: 'OPERAÇÃO' },
  { icon: Flame, label: 'Mapa de Calor (Ticket)', id: 'mapa-calor', category: 'ANÁLISES & IA' },
  { icon: Users, label: 'Motoristas', id: 'motoristas', category: 'CADASTROS' },
  { icon: Car, label: 'Veículos', id: 'veiculos', category: 'CADASTROS' },
  { icon: ClipboardText, label: 'Jornadas', id: 'jornadas', category: 'OPERAÇÃO' },
  { icon: Drop, label: 'Abastecimentos', id: 'abastecimentos', category: 'OPERAÇÃO' },
  { icon: Wrench, label: 'Manutenções', id: 'manutencoes', category: 'OPERAÇÃO' },
  { icon: Target, label: 'Metas & Bônus', id: 'metas', category: 'ANÁLISES & IA' },
  { icon: CurrencyDollar, label: 'Tarifas Particulares', id: 'tarifas-particulares', category: 'CONFIGURAÇÕES' },
  { icon: Image, label: 'Gestão de Mídias', id: 'gestao-midias', category: 'CONFIGURAÇÕES' },
  { icon: Gear, label: 'Configurações', id: 'configuracoes', category: 'CONFIGURAÇÕES' },
];

interface AppSidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export function AppSidebar({ activeView, onNavigate, isMobileOpen = false, onCloseMobile }: AppSidebarProps) {
  const { logout, user } = useAuth();
  const showTarifas = user?.role === 'ADMIN' || user?.role === 'GESTOR';

  const filteredItems = navItems.filter(
    (item) => (item.id !== 'tarifas-particulares' && item.id !== 'gestao-midias') || showTarifas
  );

  const categories = Array.from(new Set(filteredItems.map((i) => i.category || 'GERAL')));

  const handleItemClick = (id: string) => {
    onNavigate(id);
    if (onCloseMobile) onCloseMobile();
  };

  const renderContent = () => (
    <div className="flex flex-col h-full bg-slate-950/95 backdrop-blur-2xl text-slate-100 border-r border-slate-800/80 shadow-2xl">
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/app-logo.png" alt="App Jornada Logo" className="w-10 h-10 rounded-xl shadow-lg shadow-cyan-500/20 object-cover border border-slate-700/60" />
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">App Jornada</h1>
            <p className="text-[10px] text-teal-400 font-semibold tracking-wider uppercase">Fluent Fleet OS</p>
          </div>
        </div>
        
        {/* Botão fechar apenas no Mobile */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="md:hidden p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
          >
            <X size={20} />
          </button>
        )}
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-4">
        {categories.map((cat) => {
          const itemsInCat = filteredItems.filter((i) => (i.category || 'GERAL') === cat);
          return (
            <div key={cat} className="space-y-1">
              <div className="px-3 text-[10px] font-bold text-slate-500 tracking-wider uppercase">
                {cat}
              </div>
              {itemsInCat.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                    className={cn(
                      'w-full flex items-center gap-3.5 px-3.5 py-2.5 text-left rounded-xl transition-all duration-200 text-sm font-medium',
                      'hover:bg-slate-800/60 hover:text-white',
                      isActive && 'bg-teal-500/15 text-teal-300 border border-teal-500/30 font-semibold shadow-md shadow-teal-950/40'
                    )}
                  >
                    <Icon size={20} className={cn('flex-shrink-0', isActive ? 'text-teal-400' : 'text-slate-400')} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-800/80 flex flex-col gap-2 bg-slate-950/60">
        <a
          href="/app-jornada-v1.0.8.apk"
          download="app-jornada-v1.0.8.apk"
          className="w-full flex items-center gap-3 px-3.5 py-2.5 text-left text-xs rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 font-semibold transition-all duration-200 border border-emerald-500/30 shadow-sm"
          title="Baixar App Motorista Versão v1.0.8 (APK)"
        >
          <DownloadSimple size={18} className="flex-shrink-0 text-emerald-400 animate-bounce" />
          <div className="flex flex-col">
            <span className="font-bold">Baixar App Motorista</span>
            <span className="text-[10px] text-emerald-400/80">v1.0.8 (APK)</span>
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
          Fluent 2 • v1.0.8 • 2026
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Fixed Sidebar */}
      <aside className="hidden md:block fixed left-0 top-0 h-screen w-64 z-50">
        {renderContent()}
      </aside>

      {/* Mobile Drawer Slide-over Sheet */}
      {isMobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop overlay */}
          <div 
            className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobile}
          />
          {/* Slide-in Menu */}
          <div className="relative w-80 max-w-[85vw] h-full z-10 shadow-2xl transform transition-transform duration-300">
            {renderContent()}
          </div>
        </div>
      )}
    </>
  );
}
