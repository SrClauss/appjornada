import { Navigate, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/shared/Sidebar'
import { ProtectedRoute } from './components/shared/ProtectedRoute'
import { LoginPage } from './pages/Login/LoginPage'
import { DashboardPage } from './pages/Dashboard/DashboardPage'
import { MotoristasPage } from './pages/Motoristas/MotoristasPage'
import { JornadasPage } from './pages/Jornadas/JornadasPage'
import { VeiculosPage } from './pages/Veiculos/VeiculosPage'
import { ManutencoesPage } from './pages/Manutencoes/ManutencoesPage'
import { MetasPage } from './pages/Metas/MetasPage'
import { RelatoriosPage } from './pages/Relatorios/RelatoriosPage'

function AppLayout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="content-shell">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/motoristas" element={<MotoristasPage />} />
          <Route path="/jornadas" element={<JornadasPage />} />
          <Route path="/veiculos" element={<VeiculosPage />} />
          <Route path="/manutencoes" element={<ManutencoesPage />} />
          <Route path="/metas" element={<MetasPage />} />
          <Route path="/relatorios" element={<RelatoriosPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/*" element={<AppLayout />} />
      </Route>
    </Routes>
  )
}
