import { LogOut, MoreHorizontal, Upload, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { Avatar, NavCount, SoonBadge } from './AppShellParts'
import { Button } from './Button'
import {
  NAV_ITEMS,
  initialsOf,
  isActivePath,
  type AppShellCounts,
  type AppShellUser,
  type AppShellWorkspace,
} from './appShellNav'

interface CompactNavProps {
  user?: AppShellUser
  workspace?: AppShellWorkspace
  counts?: AppShellCounts
  onSignOut?: () => void
  onUpload?: () => void
}

function MoreSheet({
  user,
  workspace,
  counts,
  onSignOut,
  onClose,
}: Omit<CompactNavProps, 'onUpload'> & { onClose: () => void }) {
  const { t } = useTranslation()

  // docs/11 §4.1: Esc closes the More sheet.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end" role="dialog" aria-modal="true">
      <div className="fixed inset-0 bg-inverse/40 backdrop-blur-xs" onClick={onClose} />
      <div className="relative bg-surface rounded-t-lg shadow-overlay border-t border-line p-5 flex flex-col gap-4 z-10 max-h-screen overflow-y-auto">
        <div className="flex items-center justify-between pb-3 border-b border-line">
          <strong className="text-base font-semibold">{t('nav.moreTitle')}</strong>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-sm text-ink-muted hover:bg-sunken cursor-pointer"
            aria-label={t('nav.closeMore')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.filter((item) => !item.bottomNav).map((item) => {
            const Icon = item.icon
            return (
              <Link
                key={item.key}
                to={item.path}
                onClick={onClose}
                className="flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium text-ink hover:bg-sunken transition-colors"
              >
                <Icon className="w-5 h-5 text-ink-muted" />
                <span className="flex-1">{t(`nav.${item.key}.long`)}</span>
                <NavCount item={item} counts={counts} />
                {item.p1 && <SoonBadge />}
              </Link>
            )
          })}
        </nav>

        {user && (
          <div className="pt-3 border-t border-line flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <Avatar initials={initialsOf(user.name)} />
              <div className="min-w-0">
                <strong className="block text-sm font-semibold truncate">{user.name}</strong>
                {workspace && (
                  <span className="block text-xs text-ink-muted truncate">{workspace.name}</span>
                )}
              </div>
            </div>
            {onSignOut && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  onClose()
                  onSignOut()
                }}
              >
                <LogOut className="w-4 h-4" />
                <span>{t('auth.signOut')}</span>
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function AppShellCompactNav({ user, workspace, counts, onSignOut, onUpload }: CompactNavProps) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)

  return (
    <>
      <div className="sticky bottom-0 z-30">
        <div className="absolute right-4 bottom-20 z-10">
          <Button
            variant="primary"
            size="lg"
            className="rounded-full shadow-raised px-5 h-13"
            onClick={onUpload}
          >
            <Upload className="w-5 h-5" />
            <span>{t('shell.upload')}</span>
          </Button>
        </div>

        <nav aria-label={t('nav.mobile')} className="grid grid-cols-5 p-1.5 bg-surface border-t border-line">
          {NAV_ITEMS.filter((item) => item.bottomNav).map((item) => {
            const active = isActivePath(pathname, item.path)
            const Icon = item.icon
            const alertCount =
              item.count?.tone === 'alert' ? counts?.[item.count.key] : undefined
            return (
              <Link
                key={item.key}
                to={item.path}
                aria-current={active ? 'page' : undefined}
                className={`flex flex-col items-center justify-center gap-1 py-1 text-xs relative ${
                  active ? 'text-brand font-semibold' : 'text-ink-muted'
                }`}
              >
                <div
                  className={`w-12 h-7 rounded-full grid place-items-center ${
                    active ? 'bg-brand-soft text-brand' : ''
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                </div>
                <span>{t(`nav.${item.key}.short`)}</span>
                {alertCount !== undefined && alertCount > 0 && (
                  <span className="absolute top-0.5 right-3 px-1 text-xs font-bold rounded-full bg-critical text-on-brand num leading-tight">
                    {alertCount}
                  </span>
                )}
              </Link>
            )
          })}
          <button
            type="button"
            onClick={() => setMoreOpen(true)}
            className="flex flex-col items-center justify-center gap-1 py-1 text-xs text-ink-muted cursor-pointer"
          >
            <div className="w-12 h-7 rounded-full grid place-items-center">
              <MoreHorizontal className="w-5 h-5 shrink-0" />
            </div>
            <span>{t('nav.more')}</span>
          </button>
        </nav>
      </div>

      {moreOpen && (
        <MoreSheet
          user={user}
          workspace={workspace}
          counts={counts}
          onSignOut={onSignOut}
          onClose={() => setMoreOpen(false)}
        />
      )}
    </>
  )
}
