import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

interface PlaceholderProps {
  titleKey: string
  spec: string
}

/** Routes of docs/11 §4.2 whose screens arrive with later specs (T001-16), in the kit's page frame. */
function PlaceholderPage({ titleKey, spec }: PlaceholderProps) {
  const { t } = useTranslation()
  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t(titleKey)}</h1>
        <p>{t('placeholder.body', { spec })}</p>
      </div>
      <Link className="link" to="/">
        {t('placeholder.backToDashboard')}
      </Link>
    </div>
  )
}

export const MonthsPage = () => <PlaceholderPage titleKey="placeholder.months" spec="spec 007" />
export const ReviewPage = () => <PlaceholderPage titleKey="placeholder.review" spec="spec 009" />
export const RiskPage = () => <PlaceholderPage titleKey="placeholder.risk" spec="spec 008" />
export const CounterpartiesPage = () => (
  <PlaceholderPage titleKey="placeholder.counterparties" spec="spec 014" />
)
export const AssistantPage = () => <PlaceholderPage titleKey="placeholder.assistant" spec="spec 011" />
export const LabelsPage = () => <PlaceholderPage titleKey="placeholder.labels" spec="spec 016" />
export const RunsPage = () => <PlaceholderPage titleKey="placeholder.runs" spec="spec 017" />
