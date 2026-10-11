import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { AppShellTrial } from '../shared/ui'

const WARN_DAYS = 7

/** AC-013-12 and docs/11 §7a: in the last 7 days and after expiry, say what happens. */
export function TrialBanner({ trial }: { trial: AppShellTrial }) {
  const { t } = useTranslation()
  const expired = trial.status === 'TRIAL_EXPIRED'
  if (!expired && trial.daysLeft > WARN_DAYS) return null

  return (
    <div
      role="status"
      className={`mb-5 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm border px-4 py-3 text-sm ${
        expired ? 'border-critical-line bg-critical-soft text-critical' : 'border-medium-line bg-medium-soft text-medium'
      }`}
    >
      <span className="flex-1 min-w-0">
        {expired ? t('trialBanner.expired') : t('trialBanner.endingSoon', { count: trial.daysLeft })}
      </span>
      <Link to="/settings/plan" className="font-semibold underline">
        {t('shell.planAndUsage')}
      </Link>
    </div>
  )
}
