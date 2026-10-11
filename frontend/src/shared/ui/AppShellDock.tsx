/** `div.dock` below 600 px: the floating Upload above the bottom navigation, and the More sheet. */

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Icon } from './Icon'
import { NAV_ITEMS, isActivePath, type AppShellCounts } from './appShellNav'

const IN_MORE = NAV_ITEMS.filter((item) => !item.bottomNav)

function MoreSheet({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation()

  // docs/11 §4.1: Esc or a tap outside closes the sheet.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="more-sheet block" role="dialog" aria-modal="true" aria-labelledby="more-title">
      <button type="button" className="scrim border-0" aria-label={t('nav.closeMore')} onClick={onClose} />
      <div className="sheet">
        <span className="handle" aria-hidden="true" />
        <p className="sheet-title" id="more-title">
          {t('nav.moreTitle')}
        </p>
        <nav className="sheet-links">
          {IN_MORE.map((item) => (
            <Link key={item.key} to={item.path} onClick={onClose}>
              <Icon name={item.icon} />
              <span>{t(`nav.${item.key}.long`)}</span>
              <Icon name="chevron-right" size="sm" />
            </Link>
          ))}
        </nav>
      </div>
    </div>
  )
}

interface DockProps {
  activePath: string
  counts?: AppShellCounts
  showFab: boolean
  onUpload?: () => void
  uploadBlockedReason?: string
}

export function AppShellDock({
  activePath,
  counts,
  showFab,
  onUpload,
  uploadBlockedReason,
}: DockProps) {
  const { t } = useTranslation()
  const pathname = activePath
  const [moreOpen, setMoreOpen] = useState(false)
  const inMore = IN_MORE.some((item) => isActivePath(pathname, item.path))

  return (
    <>
      <div className="dock">
        {showFab && (
          <button
            type="button"
            className="fab border-0 disabled:opacity-60"
            onClick={onUpload}
            disabled={Boolean(uploadBlockedReason)}
            title={uploadBlockedReason}
          >
            <Icon name="upload" />
            {t('shell.upload')}
          </button>
        )}
        <nav className="bottom-nav" aria-label={t('nav.mobile')}>
          {NAV_ITEMS.filter((item) => item.bottomNav).map((item) => {
            const value = item.count && !item.count.neutral ? counts?.[item.count.key] : undefined
            return (
              <Link
                key={item.key}
                className="nav-item"
                to={item.path}
                aria-current={isActivePath(pathname, item.path) ? 'page' : undefined}
              >
                <span className="nav-icon">
                  <Icon name={item.icon} />
                  {value !== undefined && value > 0 && (
                    <span className="nav-count" aria-label={t('shell.openCount', { count: value })}>
                      {value}
                    </span>
                  )}
                </span>
                {t(`nav.${item.key}.long`)}
              </Link>
            )
          })}
          <button
            type="button"
            className="nav-item border-0 bg-transparent"
            aria-current={inMore ? 'page' : undefined}
            aria-haspopup="dialog"
            onClick={() => setMoreOpen(true)}
          >
            <span className="nav-icon">
              <Icon name="menu" />
            </span>
            {t('nav.more')}
          </button>
        </nav>
      </div>
      {moreOpen && <MoreSheet onClose={() => setMoreOpen(false)} />}
    </>
  )
}
