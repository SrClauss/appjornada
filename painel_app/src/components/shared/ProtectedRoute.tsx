import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthContext } from '../../contexts/useAuthContext'

export function ProtectedRoute() {
  const { isAuthenticated, isLoading, user } = useAuthContext()
  const location = useLocation()

  if (isLoading) {
    return <p className="empty-state">Carregando sessão...</p>
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (user.role === 'MOTORISTA') {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
