import { Building2, ChevronDown, LogOut } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { Avatar, NavCount, SoonBadge, TrialCard } from './AppShellParts'
import {
  NAV_ITEMS,
  initialsOf,
  isActivePath,
  type AppShellCounts,
  type AppShellTrial,
  type AppShellUser,
  type AppShellWorkspace,
  type NavGroup,
  type NavItem,
} from './appShellNav'

interface SidebarProps {
  user?: AppShellUser
  workspace?: AppShellWorkspace
  trial?: AppShellTrial
  counts?: AppShellCounts
  onSignOut?: () => void
}

const GROUP_HEADINGS: Partial<Record<NavGroup, string>> = {
  books: 'nav.groups.books',
  insight: 'nav.groups.insight',
}

function SidebarLink({ item, counts }: { item: NavItem; counts?: AppShellCounts }) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const active = isActivePath(pathname, item.path)
  const Icon = item.icon
  return (
    <Link
      to={item.path}
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
        active ? 'bg-brand-soft text-brand font-semibold' : 'text-ink-muted hover:text-ink hover:bg-sunken'
      }`}
    >
      <Icon className="w-5 h-5 shrink-0" />
      <span className="flex-1 truncate">{t(`nav.${item.key}.long`)}</span>
      <NavCount item={item} counts={counts} />
      {item.p1 && <SoonBadge />}
    </Link>
  )
}

export function AppShellSidebar({ user, workspace, trial, counts, onSignOut }: SidebarProps) {
  const { t } = useTranslation()
  const groups: NavGroup[] = ['top', 'books', 'insight']
  const footerItems = NAV_ITEMS.filter((item) => item.group === 'footer')

  return (
    <aside
      aria-label={t('nav.sidebar')}
      className="w-62 shrink-0 min-h-screen bg-surface border-r border-line flex flex-col p-4 gap-1 sticky top-0 h-screen overflow-y-auto"
    >
      <div className="flex items-center gap-2 px-2 py-1">
        <Link to="/" aria-label={t('app.home')}>
          <img src="/brand/kredibel-logo.svg" alt={t('app.name')} className="h-8 w-auto" />
        </Link>
      </div>

      {workspace && (
        <Link
          to="/settings"
          className="flex items-center gap-2.5 p-2.5 my-3 rounded-sm bg-sunken text-ink hover:bg-line transition-colors"
        >
          <div className="w-8 h-8 rounded-sm bg-surface text-brand grid place-items-center shrink-0">
            <Building2 className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex-1">
            <strong className="block text-sm font-semibold truncate leading-tight">
              {workspace.name}
            </strong>
            {workspace.subtitle && (
              <span className="block text-xs text-ink-muted truncate">{workspace.subtitle}</span>
            )}
          </div>
          <ChevronDown className="w-4 h-4 text-ink-muted shrink-0" />
        </Link>
      )}

      <nav aria-label={t('nav.main')} className="flex flex-col gap-0.5 flex-1">
        {groups.map((group) => {
          const heading = GROUP_HEADINGS[group]
          return (
            <div key={group} className="flex flex-col gap-0.5">
              {heading && (
                <span className="text-xs font-semibold text-ink-subtle px-3 pt-3 pb-1">
                  {t(heading)}
                </span>
              )}
              {NAV_ITEMS.filter((item) => item.group === group).map((item) => (
                <SidebarLink key={item.key} item={item} counts={counts} />
              ))}
            </div>
          )
        })}
      </nav>

      <div className="flex flex-col gap-2 mt-auto pt-2 border-t border-line">
        {trial && <TrialCard trial={trial} />}
        {footerItems.map((item) => (
          <SidebarLink key={item.key} item={item} counts={counts} />
        ))}
        {user && (
          <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-sm">
            <Avatar initials={initialsOf(user.name)} />
            <div className="min-w-0 flex-1">
              <strong className="block text-sm font-semibold truncate leading-tight">{user.name}</strong>
              {user.role && (
                <span className="block text-xs text-ink-muted">{t(`roles.${user.role}`)}</span>
              )}
            </div>
            {onSignOut && (
              <button
                type="button"
                onClick={onSignOut}
                className="p-1 rounded-sm text-ink-muted hover:text-critical hover:bg-critical-soft transition-colors cursor-pointer"
                aria-label={t('auth.signOut')}
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
