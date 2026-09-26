import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import { useAuth } from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/evidence', label: 'Evidence' },
  { to: '/cases', label: 'Cases' },
  { to: '/upload', label: 'Upload' },
  { to: '/analysis', label: 'Analysis' },
  { to: '/timeline', label: 'Timeline' },
  { to: '/reports', label: 'Reports' },
]

const ADMIN_NAV_ITEMS = [
  { to: '/audit-logs', label: 'Audit Logs' },
  { to: '/users', label: 'Users' },
]

function NavLinkItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-accent-soft/20 text-accent'
            : 'text-slate-400 hover:bg-surface hover:text-slate-100'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const isAdmin = user?.role === 'admin'

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-full">
      <aside className="flex w-60 shrink-0 flex-col border-r border-edge bg-surface">
        <div className="flex items-center gap-2 border-b border-edge px-4 py-4">
          <div className="flex size-8 items-center justify-center rounded-lg bg-accent font-bold text-white">
            C
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100">CCTV Forensics</div>
            <div className="text-[11px] uppercase tracking-wider text-slate-500">
              Evidence Analyzer
            </div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => (
            <NavLinkItem key={item.to} to={item.to} label={item.label} />
          ))}
          {isAdmin && (
            <div className="pt-2">
              {ADMIN_NAV_ITEMS.map((item) => (
                <NavLinkItem key={item.to} to={item.to} label={item.label} />
              ))}
            </div>
          )}
        </nav>
        <div className="border-t border-edge p-4">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 text-xs text-slate-500">
              <div className="truncate text-slate-300">
                {user?.name ?? 'Signed out'}
              </div>
              <div className="truncate capitalize">{user?.role ?? ''}</div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="shrink-0 rounded-md border border-edge px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-surface hover:text-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto bg-ink p-6">
        <Outlet />
      </main>
    </div>
  )
}
