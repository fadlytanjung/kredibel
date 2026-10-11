import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Panel } from '../shared/ui/Panel'

interface PlaceholderProps {
  titleKey: string
  spec: string
}

/** Routes of docs/11 §4.2 whose screens arrive with later specs (T001-16). */
function PlaceholderPage({ titleKey, spec }: PlaceholderProps) {
  const { t } = useTranslation()
  return (
    <div className="max-w-4xl mx-auto">
      <Panel elevation="raised">
        <h1 className="text-xl font-bold text-ink">{t(titleKey)}</h1>
        <p className="mt-2 text-sm text-ink-muted">{t('placeholder.body', { spec })}</p>
        <Link to="/" className="inline-block mt-6 text-sm font-semibold text-brand hover:underline">
          {t('placeholder.backToDashboard')}
        </Link>
      </Panel>
    </div>
  )
}

export const DocumentsPage = () => <PlaceholderPage titleKey="placeholder.documents" spec="spec 003" />
export const MonthsPage = () => <PlaceholderPage titleKey="placeholder.months" spec="spec 007" />
export const ReviewPage = () => <PlaceholderPage titleKey="placeholder.review" spec="spec 009" />
export const RiskPage = () => <PlaceholderPage titleKey="placeholder.risk" spec="spec 008" />
export const CounterpartiesPage = () => (
  <PlaceholderPage titleKey="placeholder.counterparties" spec="spec 014" />
)
export const AssistantPage = () => <PlaceholderPage titleKey="placeholder.assistant" spec="spec 011" />
export const SettingsPage = () => <PlaceholderPage titleKey="placeholder.settings" spec="spec 013" />
