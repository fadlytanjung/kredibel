import { Link } from 'react-router-dom'

interface PlaceholderProps {
  title: string
  spec: string
}

function PlaceholderPage({ title, spec }: PlaceholderProps) {
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="border border-gray-200 rounded-xl p-8 bg-white shadow-sm">
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        <p className="mt-2 text-sm text-gray-500">
          This feature will be implemented in {spec}.
        </p>
        <div className="mt-4">
          <Link to="/" className="text-sm font-semibold text-emerald-700 hover:text-emerald-800">
            &larr; Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export const DocumentsPage = () => <PlaceholderPage title="Documents" spec="Spec 003 (Document Intake)" />
export const MonthsPage = () => <PlaceholderPage title="Reconciliation (Months)" spec="Spec 007 (Reconciliation)" />
export const ReviewPage = () => <PlaceholderPage title="Review Queue" spec="Spec 009 (Review Queue)" />
export const RiskPage = () => <PlaceholderPage title="Risk & Explanations" spec="Spec 008 (Risk & Explanations)" />
export const CounterpartiesPage = () => <PlaceholderPage title="Clients & Suppliers" spec="Spec 014 (Counterparties)" />
export const SettingsPage = () => <PlaceholderPage title="Settings & Plans" spec="Spec 013 (Workspace & Plans)" />
