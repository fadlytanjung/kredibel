/** GET /api/workspace → what the app shell shows (AC-001-16, AC-013-12). Pure. */

import type { components } from '../../shared/api/schema'
import type { AppShellTrial, AppShellWorkspace } from '../../shared/ui'

export type Workspace = components['schemas']['Workspace']

export interface WorkspaceShellProps {
  workspace: AppShellWorkspace
  trial?: AppShellTrial
  /** Upload is refused by the server after the trial (AC-013-8); the UI says why first. */
  uploadBlocked: boolean
}

export function shellPropsFromWorkspace(ws: Workspace): WorkspaceShellProps {
  const sub = ws.subscription
  const framework = ws.profile?.accountingFramework
  const subtitle = [ws.entityType, ws.currency, framework].filter(Boolean).join(' · ')
  const trial =
    sub.status === 'ACTIVE'
      ? undefined
      : {
          status: sub.status,
          daysLeft: sub.trialDaysLeft ?? 0,
          pagesUsed: ws.usage?.extractedPages ?? 0,
          pagesMax: sub.limits?.extractedPagesPerMonth ?? 0,
        }
  return {
    workspace: { name: ws.name, subtitle },
    trial,
    uploadBlocked: sub.status === 'TRIAL_EXPIRED',
  }
}
