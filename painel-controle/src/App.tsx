import { useState } from 'react';
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
import { RelatoriosView } from '@/views/RelatoriosView';
import { ConfiguracoesView } from '@/views/ConfiguracoesView';
import { ColetaView } from '@/views/ColetaView';
import { Skeleton } from '@/components/ui/skeleton';
import { Toaster } from '@/components/ui/sonner';

function App() {
  const { user, isLoading, setupNeeded } = useAuth();
  const [activeView, setActiveView] = useState('dashboard');

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

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':      return <DashboardView />;
      case 'motoristas':     return <MotoristasView />;
      case 'veiculos':       return <VeiculosView />;
      case 'jornadas':       return <JornadasView />;
      case 'abastecimentos': return <AbastecimentosView />;
      case 'manutencoes':    return <ManutencoesView />;
      case 'metas':          return <MetasView />;
      case 'relatorios':     return <RelatoriosView />;
      case 'coleta':          return <ColetaView />;
      case 'configuracoes':  return <ConfiguracoesView />;
      default:               return <DashboardView />;
    }
  };

  return (
    <div className="flex h-screen bg-background">
      <AppSidebar activeView={activeView} onNavigate={setActiveView} />

      <div className="flex-1 flex flex-col ml-64">
        <AppHeader />

        <main className="flex-1 overflow-y-auto p-6">
          {renderView()}
        </main>
      </div>

      <Toaster />
    </div>
  );
}

export default App;