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

/** Two short lines at the sidebar foot; the whole row opens Plan and usage (docs/11 §4.1). */
export function TrialStatus({ trial }: { trial: AppShellTrial }) {
  const { t } = useTranslation()
  const ended = trial.status === 'TRIAL_EXPIRED'
  const percent = Math.min(100, Math.round((trial.pagesUsed / Math.max(1, trial.pagesMax)) * 100))
  return (
    <Link
      className={`trial-status${ended ? ' is-ended' : ''}`}
      to="/settings/plan"
      title={t('shell.planAndUsage')}
    >
      <div className="trial-head">
        <strong>{ended ? t('shell.trialEndedCard') : t('shell.trialDaysLeft', { count: trial.daysLeft })}</strong>
        <span className="pages">{t('shell.pagesShort', { used: trial.pagesUsed, max: trial.pagesMax })}</span>
      </div>
      <span className="bar" aria-hidden="true">
        <i style={{ width: `${percent}%` }} /* allow-raw-style: computed meter width */ />
      </span>
    </Link>
  )
}

/** The avatar, name and role in one link to Settings; the rail shows the avatar alone. */
function ProfileLink({ user, activePath }: { user: AppShellUser; activePath: string }) {
  const { t } = useTranslation()
  const role = user.role ? t(`roles.${user.role}`) : null
  const label = role
    ? t('shell.profileWithRole', { name: user.name, role })
    : t('shell.profile', { name: user.name })
  return (
    <Link
      className="user"
      to="/settings/profile"
      title={t('nav.settings.long')}
      aria-label={label}
      aria-current={isActivePath(activePath, '/settings') ? 'page' : undefined}
    >
      <span className="avatar" aria-hidden="true">
        {initialsOf(user.name)}
      </span>
      <span>
        <strong>{user.name}</strong>
        {role}
      </span>
      <Icon name="sliders" className="user-action" />
    </Link>
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
        {trial && <TrialStatus trial={trial} />}
        {user && <ProfileLink user={user} activePath={activePath} />}
      </div>
    </aside>
  )
}
