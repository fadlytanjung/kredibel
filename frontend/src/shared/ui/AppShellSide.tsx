/** `aside.side`: labelled sidebar from 1200 px, rail from 600 px (kit container queries). */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Icon } from './Icon'
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

export function NavLink({
  item,
  counts,
  activePath,
}: {
  item: NavItem
  counts?: AppShellCounts
  activePath: string
}) {
  const { t } = useTranslation()
  const value = item.count ? counts?.[item.count.key] : undefined
  const label = t(`nav.${item.key}.long`)
  return (
    <Link
      className="nav-item"
      to={item.path}
      title={label}
      aria-current={isActivePath(activePath, item.path) ? 'page' : undefined}
    >
      <span className="nav-icon">
        <Icon name={item.icon} />
      </span>
      <span className="nav-label-long hide-below-large">{label}</span>
      <span className="nav-label-short hide-large">{t(`nav.${item.key}.short`)}</span>
      {value !== undefined && item.count && (
        <span
          className={`nav-count${item.count.neutral ? ' is-neutral' : ''}`}
          aria-label={t('shell.itemsCount', { count: value })}
        >
          {value}
        </span>
      )}
    </Link>
  )
}

function group(name: NavGroup) {
  return NAV_ITEMS.filter((item) => item.group === name)
}

export function TrialCard({ trial }: { trial: AppShellTrial }) {
  const { t } = useTranslation()
  const percent = Math.min(100, Math.round((trial.pagesUsed / Math.max(1, trial.pagesMax)) * 100))
  return (
    <div className="trial-card">
      <strong>
        {trial.status === 'TRIAL_EXPIRED'
          ? t('shell.trialEndedCard')
          : t('shell.trialDaysLeft', { count: trial.daysLeft })}
      </strong>
      <span>{t('shell.pagesUsed', { used: trial.pagesUsed, max: trial.pagesMax })}</span>
      <span className="bar">
        <i style={{ width: `${percent}%` }} /* allow-raw-style: computed meter width */ />
      </span>
      <Link to="/settings/plan">{t('shell.planAndUsage')}</Link>
    </div>
  )
}

interface SideProps {
  user?: AppShellUser
  workspace?: AppShellWorkspace
  trial?: AppShellTrial
  counts?: AppShellCounts
  activePath: string
}

export function AppShellSide({ user, workspace, trial, counts, activePath }: SideProps) {
  const { t } = useTranslation()
  const links = (name: NavGroup) =>
    group(name).map((item) => (
      <NavLink key={item.key} item={item} counts={counts} activePath={activePath} />
    ))

  const nav = {
    main: links('main'),
    books: links('books'),
    insight: links('insight'),
    ai: links('ai'),
    foot: links('foot'),
  }

  return (
    <aside className="side">
      <Link to="/" aria-label={t('app.home')}>
        <img className="lockup" src="/brand/kredibel-logo.svg" alt={t('app.name')} />
        <img className="side-mark" src="/brand/kredibel-mark.svg" alt={t('app.name')} />
      </Link>
      {workspace && (
        <Link className="workspace" to="/settings/profile">
          <span className="ws-icon">
            <Icon name="building" />
          </span>
          <span>
            <strong>{workspace.name}</strong>
            {workspace.subtitle && <span className="sub">{workspace.subtitle}</span>}
          </span>
          <Icon name="chevron-down" size="sm" />
        </Link>
      )}
      <nav className="nav" aria-label={t('nav.main')}>
        {nav.main}
        <span className="nav-group-label">{t('nav.groups.books')}</span>
        {nav.books}
        <span className="nav-group-label">{t('nav.groups.insight')}</span>
        <span className="nav-sep" aria-hidden="true" />
        {nav.insight}
        <span className="nav-group-label">{t('nav.groups.ai')}</span>
        <span className="nav-sep" aria-hidden="true" />
        {nav.ai}
      </nav>
      <div className="side-foot">
        {trial && <TrialCard trial={trial} />}
        <nav className="nav" aria-label={t('nav.settingsNav')}>
          {nav.foot}
        </nav>
        {user && (
          <Link className="user" to="/settings/profile">
            <span className="avatar" role="img" aria-label={t('shell.signedInAs', { name: user.name })}>
              {initialsOf(user.name)}
            </span>
            <span>
              <strong>{user.name}</strong>
              {user.role ? t(`roles.${user.role}`) : null}
            </span>
          </Link>
        )}
      </div>
    </aside>
  )
}
