import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { LoginPage } from '@/pages/LoginPage';
import { SetupPage } from '@/pages/SetupPage';
import { AppSidebar } from '@/components/AppSidebar';
import { AppHeader } from '@/components/AppHeader';
import { DashboardView } from '@/views/DashboardView';
import { MotoristasView } from '@/views/MotoristasView';
import { VeiculosView } from '@/views/VeiculosView';
import { JornadasView } from '@/views/JornadasView';
import { AbastecimentosView } from '@/views/AbastecimentosView';
import { ManutencoesView } from '@/views/ManutencoesView';
import { MetasView } from '@/views/MetasView';
import { ConfiguracoesView } from '@/views/ConfiguracoesView';
import { PrecosParticularesView } from '@/views/PrecosParticularesView';
import { MediaManagementView } from '@/views/MediaManagementView';
import { MonitorView } from '@/views/MonitorView';
import { MapaCalorView } from '@/views/MapaCalorView';
import { Skeleton } from '@/components/ui/skeleton';
import { Toaster } from '@/components/ui/sonner';

function App() {
  const { user, isLoading, setupNeeded } = useAuth();
  
  const [activeView, setActiveView] = useState(() => {
    const hash = window.location.hash;
    return hash.startsWith('#/') ? hash.slice(2) : 'dashboard';
  });

  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      const view = hash.startsWith('#/') ? hash.slice(2) : 'dashboard';
      setActiveView(view);
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const handleNavigate = (view: string) => {
    window.location.hash = `/${view}`;
    setIsMobileMenuOpen(false);
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="space-y-3 w-64">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-6 w-3/4" />
          <Skeleton className="h-6 w-1/2" />
        </div>
      </div>
    );
  }

  if (setupNeeded) {
    return (
      <>
        <SetupPage />
        <Toaster />
      </>
    );
  }

  if (!user) {
    return (
      <>
        <LoginPage />
        <Toaster />
      </>
    );
  }

  if (activeView === 'monitor') {
    return (
      <div className="flex h-screen w-screen bg-slate-950 overflow-y-auto">
        <div className="flex-1">
          <MonitorView />
        </div>
        <Toaster />
      </div>
    );
  }

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':      return <DashboardView />;
      case 'motoristas':     return <MotoristasView />;
      case 'veiculos':       return <VeiculosView />;
      case 'jornadas':       return <JornadasView />;
      case 'abastecimentos': return <AbastecimentosView />;
      case 'manutencoes':    return <ManutencoesView />;
      case 'metas':          return <MetasView />;
      case 'mapa-calor':     return <MapaCalorView />;
      case 'configuracoes':  return <ConfiguracoesView />;
      case 'tarifas-particulares': return <PrecosParticularesView />;
      case 'gestao-midias':  return <MediaManagementView />;
      default:               return <DashboardView />;
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <AppSidebar
        activeView={activeView}
        onNavigate={handleNavigate}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      <div className="flex-1 flex flex-col md:ml-64 ml-0 min-w-0">
        <AppHeader onToggleMobileMenu={() => setIsMobileMenuOpen((prev) => !prev)} />

        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {renderView()}
        </main>
      </div>

      <Toaster />
    </div>
  );
}

export default App;