import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/motoristas', label: 'Motoristas' },
  { to: '/jornadas', label: 'Jornadas' },
  { to: '/veiculos', label: 'Veículos' },
  { to: '/manutencoes', label: 'Manutenções' },
  { to: '/metas', label: 'Metas' },
  { to: '/relatorios', label: 'Relatórios' },
]

export function Sidebar() {
  return (
    <aside className="sidebar">
      <h1>App Jornada</h1>
      <nav>
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === '/'}
            className={({ isActive }) => (isActive ? 'active' : '')}
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
