/**
 * Settings (design/mocks/plan-usage.html, docs/11 §6.9): the page head, the section subnav and the
 * chosen section. Team arrives with P1 roles and is shown disabled.
 */

import { useTranslation } from 'react-i18next'
import { Link, Navigate, useParams } from 'react-router-dom'
import { usePlans } from '../entities/plan'
import { useAuth } from '../entities/session'
import { useWorkspace } from '../entities/workspace'
import { BankAccountsSection } from '../features/manage-bank-accounts/BankAccountsSection'
import { ProfileForm } from '../features/update-profile/ProfileForm'
import { SETTINGS_SECTIONS, type SettingsSection } from '../shared/ui'
import { Skeleton } from '../shared/ui/Skeleton'
import { LanguageSettings } from '../widgets/LanguageSettings'
import { PlanAndUsage } from '../widgets/PlanAndUsage'

function isSection(value: string | undefined): value is SettingsSection {
  return SETTINGS_SECTIONS.includes(value as SettingsSection)
}

function Account() {
  const { t } = useTranslation('settings')
  const { user, signOut } = useAuth()
  return (
    <section className="panel panel-pad spread" aria-label={t('profile.account')}>
      <div className="stack gap-1">
        <h2 className="type-h3">{t('profile.account')}</h2>
        <p className="muted small">{t('profile.signedInAs', { email: user?.email ?? '' })}</p>
      </div>
      <button type="button" className="button button-secondary" onClick={() => void signOut()}>
        {t('profile.signOut')}
      </button>
    </section>
  )
}

export function SettingsPage() {
  const { t } = useTranslation('settings')
  const { section } = useParams()
  const workspace = useWorkspace()
  const plans = usePlans()

  if (!isSection(section) || section === 'members') return <Navigate to="/settings/plan" replace />

  const ready = workspace.data && plans.data
  const body = !ready ? (
    <Skeleton className="h-64" />
  ) : section === 'plan' ? (
    <PlanAndUsage workspace={workspace.data} catalog={plans.data} />
  ) : section === 'profile' ? (
    <div className="stack gap-6">
      <ProfileForm workspace={workspace.data} />
      <Account />
    </div>
  ) : section === 'bank-accounts' ? (
    <BankAccountsSection />
  ) : (
    <LanguageSettings workspace={workspace.data} catalog={plans.data} />
  )

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t('title')}</h1>
      </div>
      <div className="settings-layout">
        <nav className="subnav" aria-label={t('sectionsLabel')}>
          {SETTINGS_SECTIONS.map((key) =>
            key === 'members' ? (
              // P1 (roles): shown in the subnav like the others, but not a link yet.
              <a key={key} role="link" aria-disabled="true" className="cursor-default">
                {t(`sections.${key}`)}
              </a>
            ) : (
              <Link key={key} to={`/settings/${key}`} aria-current={key === section ? 'page' : undefined}>
                {t(`sections.${key}`)}
              </Link>
            ),
          )}
        </nav>
        {body}
      </div>
    </div>
  )
}
