import { NavLink, Outlet } from 'react-router-dom'
import { LayoutDashboard, Landmark, ListChecks, PiggyBank, Receipt, Wallet } from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/', label: 'ダッシュボード', icon: LayoutDashboard },
  { to: '/transactions', label: '取引管理', icon: Receipt },
  { to: '/budgets', label: '予算管理', icon: PiggyBank },
  { to: '/category-rules', label: '分類ルール', icon: ListChecks },
  { to: '/accounts', label: '口座管理', icon: Landmark },
]

export function AppShell() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
          <div className="flex items-center gap-2 font-semibold text-foreground">
            <Wallet className="size-5 text-primary" />
            <span>統合資産・経費管理</span>
          </div>
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-secondary text-secondary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )
                }
              >
                <Icon className="size-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  )
}
