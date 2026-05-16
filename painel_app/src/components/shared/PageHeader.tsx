import { useAuthContext } from '../../contexts/useAuthContext'

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const { user, logout } = useAuthContext()

  return (
    <header className="page-header">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      <div className="page-header-actions">
        <span>{user?.nome}</span>
        <button type="button" onClick={logout}>Sair</button>
      </div>
    </header>
  )
}
