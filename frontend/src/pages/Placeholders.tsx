import { Link } from 'react-router-dom'
import { Panel } from '../shared/ui/Panel'

interface PlaceholderProps {
  title: string
  spec: string
}

function PlaceholderPage({ title, spec }: PlaceholderProps) {
  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto">
      <Panel className="p-8 bg-surface border border-line rounded-md shadow-raised">
        <h2 className="text-xl font-bold text-ink">{title}</h2>
        <p className="mt-2 text-sm text-ink-muted">
          This feature will be connected in {spec}. The full interactive HTML prototype is available in design mocks.
        </p>
        <div className="mt-6 flex items-center gap-4">
          <Link to="/" className="text-sm font-semibold text-brand hover:underline">
            &larr; Back to Dashboard
          </Link>
        </div>
      </Panel>
    </div>
  )
}

export const DocumentsPage = () => <PlaceholderPage title="Documents Library" spec="Spec 003 (Document Intake)" />
export const MonthsPage = () => <PlaceholderPage title="Reconciliation (Months)" spec="Spec 007 (Reconciliation)" />
export const ReviewPage = () => <PlaceholderPage title="Review Queue" spec="Spec 009 (Review Queue)" />
export const RiskPage = () => <PlaceholderPage title="Risk & Explanations" spec="Spec 008 (Risk & Explanations)" />
export const CounterpartiesPage = () => <PlaceholderPage title="Clients & Suppliers" spec="Spec 014 (Counterparties)" />
export const SettingsPage = () => <PlaceholderPage title="Settings & Plans" spec="Spec 013 (Workspace & Plans)" />
