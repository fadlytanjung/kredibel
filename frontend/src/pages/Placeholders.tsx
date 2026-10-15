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
      <Link className="link" to="/dashboard">
        {t('placeholder.backToDashboard')}
      </Link>
    </div>
  )
}

export const CounterpartiesPage = () => (
  <PlaceholderPage titleKey="placeholder.counterparties" spec="spec 014" />
)
export const LabelsPage = () => <PlaceholderPage titleKey="placeholder.labels" spec="spec 016" />
export const RunsPage = () => <PlaceholderPage titleKey="placeholder.runs" spec="spec 017" />
