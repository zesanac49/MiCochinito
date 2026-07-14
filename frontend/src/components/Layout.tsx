import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  BarChart3,
  Building2,
  CircleUser,
  Dices,
  Gavel,
  HandCoins,
  LogOut,
  type LucideIcon,
  ScrollText,
  ShieldCheck,
  Users,
  Wallet,
} from 'lucide-react'
import { rolActivo, useAuth } from '@/store/auth'
import { cn } from '@/lib/cn'
import { SelectorNatillera } from '@/components/SelectorNatillera'

interface ItemNav {
  to: string
  icon: LucideIcon
  texto: string
  end?: boolean
}

const NAV: ItemNav[] = [
  { to: '/', icon: Wallet, texto: 'Resumen', end: true },
  { to: '/natillera', icon: Building2, texto: 'Natillera' },
  { to: '/participantes', icon: Users, texto: 'Participantes' },
  { to: '/pagos', icon: CircleUser, texto: 'Recaudo (cuotas)' },
  { to: '/prestamos', icon: HandCoins, texto: 'Préstamos' },
  { to: '/multas', icon: ScrollText, texto: 'Multas' },
  { to: '/actividades', icon: Dices, texto: 'Actividades' },
  { to: '/reportes', icon: BarChart3, texto: 'Reportes' },
  { to: '/liquidacion', icon: Gavel, texto: 'Liquidación' },
]

// Solo el administrador de la natillera activa gestiona accesos (RF-1002).
const NAV_ADMIN: ItemNav = { to: '/usuarios', icon: ShieldCheck, texto: 'Usuarios' }

export function Layout() {
  const usuario = useAuth((s) => s.usuario)
  // Suscribirse a la natillera activa hace que el menú se recalcule al cambiarla.
  useAuth((s) => s.natilleraUuid)
  const limpiar = useAuth((s) => s.limpiar)
  const navigate = useNavigate()

  const items = rolActivo() === 'ADMINISTRADOR' ? [...NAV, NAV_ADMIN] : NAV

  function salir() {
    limpiar()
    navigate('/login')
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col gap-4 p-4 md:flex-row md:p-6">
      {/* Riel de navegación extruido. */}
      <aside className="rounded-nm bg-surface-raised p-4 shadow-nm md:w-60 md:shrink-0">
        <div className="mb-5 hidden items-center gap-3 md:flex">
          <img
            src="/logo.png"
            alt="Mi Cochinito"
            className="h-10 w-10 shrink-0 rounded-nm-sm object-cover shadow-nm"
          />
          <div className="min-w-0">
            <p className="text-lg font-bold leading-tight tracking-tight">Mi Cochinito</p>
            <p className="truncate text-xs text-text-secondary">{usuario?.nombre}</p>
          </div>
        </div>
        <div className="mb-4">
          <SelectorNatillera />
        </div>
        <nav className="flex gap-2 md:flex-col">
          {items.map(({ to, icon: Icon, texto, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  'flex flex-1 items-center gap-3 rounded-nm-sm px-3 py-2.5 text-sm font-medium transition-nm',
                  isActive
                    ? 'text-accent shadow-nm-in'
                    : 'text-text-secondary hover:text-text-primary',
                )
              }
            >
              <Icon size={18} />
              <span className="hidden md:inline">{texto}</span>
            </NavLink>
          ))}
          <button
            onClick={salir}
            className="flex items-center gap-3 rounded-nm-sm px-3 py-2.5 text-sm font-medium text-text-secondary transition-nm hover:text-danger"
          >
            <LogOut size={18} />
            <span className="hidden md:inline">Salir</span>
          </button>
        </nav>
      </aside>

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
