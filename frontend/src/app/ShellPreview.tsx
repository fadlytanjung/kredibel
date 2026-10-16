/**
 * Dev-only page that renders the app shell with the mocks' synthetic sample data, so the
 * Playwright visual tests (AC-001-17) compare like with like. Not routed in production builds.
 */

import { useParams } from 'react-router-dom'
import { AssistantPage } from '../pages/AssistantPage'
import { CounterpartiesPage } from '../pages/CounterpartiesPage'
import { CounterpartyPage } from '../pages/CounterpartyPage'
import { ProfitLossContent } from '../pages/ProfitLossPage'
import { DashboardPage } from '../pages/DashboardPage'
import { DocumentPage } from '../pages/DocumentPage'
import { MonthPage } from '../pages/MonthPage'
import { MonthsPage } from '../pages/MonthsPage'
import { ReviewPage } from '../pages/ReviewPage'
import { DocumentsPage } from '../pages/DocumentsPage'
import { LabelsContent } from '../pages/LabelsPage'
import { RiskPage } from '../pages/RiskPage'
import { RunsContent } from '../pages/RunsPage'
import { SettingsPage } from '../pages/SettingsPage'
import { AppShell } from '../shared/ui'

// The same sample as tools/design/mocks/shell.py.
const PREVIEW_PROPS = {
  user: { name: 'Maya Sari', role: 'owner' },
  workspace: { name: 'Sunrise Coffee Roasters', subtitle: 'Company, IDR, IFRS' },
  trial: { status: 'TRIALING' as const, daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 92, review: 10, risk: 2, labels: 37 },
  // Take the tour is in the app's top bar (spec 021); the tour preview starts it from the address.
  onTour: () => undefined,
}

export function ShellPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/dashboard" onUpload={() => undefined}>
      <DashboardPage />
    </AppShell>
  )
}

/** Settings inside the shell, for the visual tests; the tests serve its API data. */
export function SettingsPreview() {
  const { section = 'plan' } = useParams()
  return (
    <AppShell {...PREVIEW_PROPS} activePath={`/settings/${section}`} onUpload={() => undefined}>
      <SettingsPage />
    </AppShell>
  )
}

/** One document inside the shell; the caller serves its API data and page images (screenshots). */
export function DocumentPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/documents" onUpload={() => undefined}>
      <DocumentPage />
    </AppShell>
  )
}

/** One month inside the shell; the caller serves its API data (screenshots). */
export function MonthPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/months" onUpload={() => undefined}>
      <MonthPage />
    </AppShell>
  )
}

/** All months inside the shell; the caller serves its API data (screenshots). */
export function MonthsPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/months" onUpload={() => undefined}>
      <MonthsPage />
    </AppShell>
  )
}

/** Review inside the shell, for the visual tests; the tests serve its API data. */
export function ReviewPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/review" onUpload={() => undefined}>
      <ReviewPage />
    </AppShell>
  )
}

/** The documents page inside the shell; Playwright serves the fixture's uploads (spec 003). */
export function DocumentsPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/documents" onUpload={() => undefined}>
      <DocumentsPage />
    </AppShell>
  )
}

/** The risk page inside the shell; Playwright serves the fixture's findings and documents. */
export function RiskPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/risk" onUpload={() => undefined}>
      <RiskPage />
    </AppShell>
  )
}

/** The labels page inside the shell; Playwright serves the fixture's labels (spec 016). */
export function LabelsPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/labels" onUpload={() => undefined}>
      <LabelsContent canDecide basePath="/preview/labels" />
    </AppShell>
  )
}

/** The runs page inside the shell; Playwright serves the fixture's runs and events (spec 017). */
export function RunsPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/runs" onUpload={() => undefined}>
      <RunsContent role={new URLSearchParams(window.location.search).get('role') ?? 'owner'} basePath="/preview/runs" />
    </AppShell>
  )
}

/** Synthetic P&L preview; Playwright provides all API responses. */
export function ProfitLossPreview() {
  return <AppShell {...PREVIEW_PROPS} activePath="/profit-loss" onUpload={() => undefined}>
    <ProfitLossContent canEdit />
  </AppShell>
}

/** Assistant inside the shell, for screen tests with synthetic dev mocks. */
export function AssistantPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/assistant" onUpload={() => undefined}>
      <AssistantPage />
    </AppShell>
  )
}

/** Clients and suppliers inside the shell; the caller serves its API data (screenshots). */
export function CounterpartiesPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/counterparties" onUpload={() => undefined}>
      <CounterpartiesPage />
    </AppShell>
  )
}

/** One client or supplier inside the shell; the caller serves its API data (screenshots). */
export function CounterpartyPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/counterparties" onUpload={() => undefined}>
      <CounterpartyPage />
    </AppShell>
  )
}
