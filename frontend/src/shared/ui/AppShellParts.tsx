import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { AppShellCounts, AppShellTrial, NavItem } from './appShellNav'

export function NavCount({ item, counts }: { item: NavItem; counts?: AppShellCounts }) {
  const value = item.count ? counts?.[item.count.key] : undefined
  if (value === undefined || !item.count) return null
  const tone =
    item.count.tone === 'neutral' ? 'bg-sunken text-ink-muted' : 'bg-critical text-on-brand'
  return <span className={`px-1.5 py-0.5 text-xs font-bold rounded-full num ${tone}`}>{value}</span>
}

export function SoonBadge() {
  const { t } = useTranslation()
  return (
    <span className="px-1.5 py-0.5 text-xs font-semibold rounded-xs bg-sunken text-ink-muted">
      {t('nav.p1Badge')}
    </span>
  )
}

export function TrialCard({ trial }: { trial: AppShellTrial }) {
  const { t } = useTranslation()
  const percent = Math.min(100, Math.round((trial.pagesUsed / Math.max(1, trial.pagesMax)) * 100))
  return (
    <div className="p-3 rounded-md bg-inverse text-on-inverse text-xs flex flex-col gap-1.5">
      <strong className="text-sm font-semibold">
        {t('shell.trialDaysLeft', { count: trial.daysLeft })}
      </strong>
      <span className="text-on-inverse/80">
        {t('shell.pagesUsed', { used: trial.pagesUsed, max: trial.pagesMax })}
      </span>
      <div className="h-1.5 rounded-full bg-surface/20 overflow-hidden mt-1">
        <div
          className="h-full bg-brand-accent rounded-full transition-all"
          style={{ width: `${percent}%` }} /* allow-raw-style: computed meter width */
        />
      </div>
      <Link to="/settings" className="text-brand-accent font-semibold hover:underline mt-0.5">
        {t('shell.planAndUsage')}
      </Link>
    </div>
  )
}

export function Avatar({ initials, title }: { initials: string; title?: string }) {
  return (
    <div
      className="w-8 h-8 rounded-full bg-brand-soft text-brand font-bold text-xs grid place-items-center shrink-0"
      title={title}
    >
      {initials}
    </div>
  )
}
