/** `header.topbar`: mark or back button, title (compact), breadcrumbs, search, bell, Upload. */

import { Fragment, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Badge } from './Badge'
import { CommandPalette } from './CommandPalette'
import { Icon } from './Icon'
import type { AppShellTrial, PageChrome } from './appShellNav'

export function TrialBadge({ trial }: { trial: AppShellTrial }) {
  const { t } = useTranslation()
  if (trial.status === 'TRIAL_EXPIRED') {
    return <Badge variant="critical">{t('shell.trialEnded')}</Badge>
  }
  // Phones get the short form so the page title keeps its room.
  return (
    <Badge variant={trial.daysLeft <= 7 ? 'medium' : 'brand'}>
      <span className="hide-compact">{t('shell.trialBadge', { count: trial.daysLeft })}</span>
      <span className="only-compact">{t('shell.trialBadgeShort', { count: trial.daysLeft })}</span>
    </Badge>
  )
}

interface TopBarProps {
  chrome: PageChrome
  riskCount?: number
  trial?: AppShellTrial
  onUpload?: () => void
  onTour?: () => void
  uploadBlockedReason?: string
  extra?: React.ReactNode
}

export function AppShellTopBar({
  chrome,
  riskCount,
  trial,
  onUpload,
  onTour,
  uploadBlockedReason,
  extra,
}: TopBarProps) {
  const { t } = useTranslation()
  const crumbText = (crumb: PageChrome['crumbs'][number]) =>
    crumb.literal ? crumb.label : t(crumb.label)
  const title = chrome.crumbs.length ? crumbText(chrome.crumbs[chrome.crumbs.length - 1]!) : ''
  const open = riskCount ?? 0
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      } else if (
        e.key === '/' &&
        !(
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement ||
          (e.target as HTMLElement)?.isContentEditable
        )
      ) {
        e.preventDefault()
        setPaletteOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
      <header className="topbar">
        {chrome.back ? (
          <Link
            className="icon-button only-compact"
            to={chrome.back.to}
            aria-label={t('shell.backTo', { page: t(chrome.back.labelKey) })}
          >
            <Icon name="chevron-left" />
          </Link>
        ) : (
          <Link className="only-compact" to="/dashboard" aria-label={t('app.home')}>
            <img className="mark" src="/brand/kredibel-mark.svg" alt={t('app.name')} />
          </Link>
        )}
        <p className="topbar-title only-compact">{title}</p>
        <nav className="crumbs" aria-label={t('nav.breadcrumbs')}>
          {chrome.crumbs.map((crumb, index) =>
            index < chrome.crumbs.length - 1 && crumb.to ? (
              <Fragment key={crumb.label}>
                <Link to={crumb.to}>{crumbText(crumb)}</Link>
                <Icon name="chevron-right" />
              </Fragment>
            ) : (
              <span key={crumb.label} aria-current="page">
                {crumbText(crumb)}
              </span>
            ),
          )}
        </nav>
        <div className="topbar-actions">
          {extra}
          {/* Below 1200 px the sidebar's trial card is hidden, so the top bar carries it (AC-013-12). */}
          {trial && (
            <span className="hide-large">
              <TrialBadge trial={trial} />
            </span>
          )}
          <button
            type="button"
            className="search-field border-0 cursor-pointer"
            onClick={() => setPaletteOpen(true)}
            title={t('shell.search')}
            aria-label={t('shell.search')}
          >
            <Icon name="search" size="sm" />
            {t('shell.search')}
            <span className="kbd">/</span>
          </button>
          {onTour && (
            <button type="button" className="icon-button" onClick={onTour} aria-label={t('shell.tour')} title={t('shell.tour')}>
              <Icon name="lightbulb" />
            </button>
          )}
          <Link
            className="icon-button"
            to="/risk"
            aria-label={open > 0 ? t('shell.notifications', { count: open }) : t('shell.notificationsNone')}
          >
            <Icon name="bell" />
            {open > 0 && <span className="dot" />}
          </Link>
        <button
          type="button"
          className="button button-primary hide-compact"
          onClick={onUpload}
          disabled={Boolean(uploadBlockedReason)}
          title={uploadBlockedReason}
          aria-describedby={uploadBlockedReason ? 'upload-blocked' : undefined}
        >
          <Icon name="upload" size="sm" />
          {t('shell.upload')}
        </button>
        {uploadBlockedReason && (
          <span id="upload-blocked" className="sr-only">
            {uploadBlockedReason}
          </span>
        )}
      </div>
    </header>
    <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
  </>
  )
}

