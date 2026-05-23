import { 
  House, 
  Users, 
  Car, 
  ClipboardText, 
  Drop,
  Wrench, 
  Target, 
  ChartBar, 
  Gear 
} from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

export interface NavItem {
  icon: React.ComponentType<{ className?: string; size?: number }>;
  label: string;
  id: string;
}

export const navItems: NavItem[] = [
  { icon: House, label: 'Dashboard', id: 'dashboard' },
  { icon: Users, label: 'Motoristas', id: 'motoristas' },
  { icon: Car, label: 'Veículos', id: 'veiculos' },
  { icon: ClipboardText, label: 'Jornadas', id: 'jornadas' },
  { icon: Drop, label: 'Abastecimentos', id: 'abastecimentos' },
  { icon: Wrench, label: 'Manutenções', id: 'manutencoes' },
  { icon: Target, label: 'Metas & Bônus', id: 'metas' },
  { icon: ChartBar, label: 'Relatórios', id: 'relatorios' },
  { icon: Gear, label: 'Configurações', id: 'configuracoes' },
];

interface AppSidebarProps {
  activeView: string;
  onNavigate: (view: string) => void;
}

export function AppSidebar({ activeView, onNavigate }: AppSidebarProps) {
  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-primary text-primary-foreground flex flex-col shadow-xl z-50">
      <div className="p-6 border-b border-primary-foreground/10">
        <h1 className="text-xl font-semibold tracking-tight">App Jornada</h1>
        <p className="text-xs text-primary-foreground/70 mt-1">Painel de Gestão</p>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-4">
        {navItems.map((item) => {
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
      
      <div className="p-4 border-t border-primary-foreground/10 text-xs text-primary-foreground/60">
        v1.0.0 • 2026
      </div>
    </aside>
  );
}
