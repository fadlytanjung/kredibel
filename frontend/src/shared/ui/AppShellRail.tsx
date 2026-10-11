import { Fragment } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { Avatar } from './AppShellParts'
import {
  NAV_ITEMS,
  initialsOf,
  isActivePath,
  type AppShellCounts,
  type AppShellUser,
} from './appShellNav'

interface RailProps {
  user?: AppShellUser
  counts?: AppShellCounts
}

export function AppShellRail({ user, counts }: RailProps) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const items = NAV_ITEMS.filter((item) => item.group !== 'footer')
  const footerItems = NAV_ITEMS.filter((item) => item.group === 'footer')

  return (
    <aside
      aria-label={t('nav.rail')}
      className="w-22 shrink-0 min-h-screen bg-surface border-r border-line flex flex-col items-center py-4 gap-2 sticky top-0 h-screen overflow-y-auto"
    >
      <Link to="/" aria-label={t('app.home')} className="mb-2">
        <img src="/brand/kredibel-mark.svg" alt={t('app.name')} className="w-10 h-10" />
      </Link>

      <nav aria-label={t('nav.main')} className="flex flex-col items-center gap-1 flex-1">
        {items.map((item, idx) => {
          const active = isActivePath(pathname, item.path)
          const Icon = item.icon
          const startsGroup = idx > 0 && items[idx - 1]?.group !== item.group && item.group !== 'books'
          const alertCount =
            item.count?.tone === 'alert' ? counts?.[item.count.key] : undefined
          return (
            <Fragment key={item.key}>
              {startsGroup && <div className="w-10 h-px bg-line my-1" />}
              <Link
                to={item.path}
                title={t(`nav.${item.key}.long`)}
                aria-current={active ? 'page' : undefined}
                className={`flex flex-col items-center justify-center gap-1 w-16 h-14 rounded-sm text-xs transition-colors relative ${
                  active ? 'text-brand font-semibold' : 'text-ink-muted hover:text-ink hover:bg-sunken'
                }`}
              >
                <div
                  className={`w-10 h-7 rounded-full grid place-items-center ${
                    active ? 'bg-brand-soft text-brand' : ''
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                </div>
                <span className="text-xs leading-none truncate max-w-full">
                  {t(`nav.${item.key}.short`)}
                </span>
                {alertCount !== undefined && alertCount > 0 && (
                  <span className="absolute top-1 right-2 px-1 text-xs font-bold rounded-full bg-critical text-on-brand num leading-tight">
                    {alertCount}
                  </span>
                )}
              </Link>
            </Fragment>
          )
        })}
      </nav>

      <div className="flex flex-col items-center gap-2 pt-2 border-t border-line w-full">
        {footerItems.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.key}
              to={item.path}
              title={t(`nav.${item.key}.long`)}
              className="w-10 h-10 rounded-sm grid place-items-center text-ink-muted hover:bg-sunken transition-colors"
            >
              <Icon className="w-5 h-5" />
            </Link>
          )
        })}
        {user && <Avatar initials={initialsOf(user.name)} title={user.name} />}
      </div>
    </aside>
  )
}
