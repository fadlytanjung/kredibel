/**
 * Dev-only page that renders the app shell with fixed synthetic props, so the Playwright visual
 * tests (AC-001-17) can screenshot it without signing in. Not routed in production builds.
 */

import { DashboardPage } from '../pages/DashboardPage'
import { AppShell } from '../shared/ui'

const PREVIEW_PROPS = {
  user: { name: 'Demo Owner', role: 'owner' },
  workspace: { name: 'Sunrise Coffee Roasters', subtitle: 'COMPANY · IDR · IFRS' },
  trial: { status: 'TRIALING' as const, daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 92, review: 9, risk: 2 },
}

export function ShellPreview() {
  return (
    <AppShell {...PREVIEW_PROPS} onSignOut={() => undefined} onUpload={() => undefined}>
      <DashboardPage />
    </AppShell>
  )
}
