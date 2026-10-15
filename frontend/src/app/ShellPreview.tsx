/**
 * Dev-only page that renders the app shell with the mocks' synthetic sample data, so the
 * Playwright visual tests (AC-001-17) compare like with like. Not routed in production builds.
 */

import { useParams } from 'react-router-dom'
import { AssistantPage } from '../pages/AssistantPage'
import { ProfitLossContent } from '../pages/ProfitLossPage'
import { DashboardPage } from '../pages/DashboardPage'
import { DocumentPage } from '../pages/DocumentPage'
import { MonthPage } from '../pages/MonthPage'
import { ReviewPage } from '../pages/ReviewPage'
import { SettingsPage } from '../pages/SettingsPage'
import { AppShell } from '../shared/ui'

// The same sample as tools/design/mocks/shell.py.
const PREVIEW_PROPS = {
  user: { name: 'Maya Sari', role: 'owner' },
  workspace: { name: 'Sunrise Coffee Roasters', subtitle: 'Company, IDR, IFRS' },
  trial: { status: 'TRIALING' as const, daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 92, review: 9, risk: 2, labels: 37 },
}

export function ShellPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/" onUpload={() => undefined}>
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

/** Review inside the shell, for the visual tests; the tests serve its API data. */
export function ReviewPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} activePath="/review" onUpload={() => undefined}>
      <ReviewPage />
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
