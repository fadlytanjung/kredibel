/**
 * The app shell of the mocks (tools/design/mocks/shell.py, docs/11 §4.1, docs/12 §5, AC-001-16):
 * `.viewport > .app > aside.side + .main(header.topbar, main#content, .dock)`. The kit's container
 * queries turn the sidebar into a rail from 600 px and into the bottom navigation below.
 * Presentational: everything it shows comes in as props.
 */

import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { AppShellDock } from './AppShellDock'
import { AppShellSide } from './AppShellSide'
import { AppShellTopBar } from './AppShellTopBar'
import {
  chromeFor,
  type AppShellCounts,
  type AppShellTrial,
  type AppShellUser,
  type AppShellWorkspace,
} from './appShellNav'

export type { AppShellCounts, AppShellTrial, AppShellUser, AppShellWorkspace } from './appShellNav'

export interface AppShellProps {
  children: ReactNode
  user?: AppShellUser
  workspace?: AppShellWorkspace
  trial?: AppShellTrial
  counts?: AppShellCounts
  onUpload?: () => void
  /** Spec 021: Take the tour, in the top bar. */
  onTour?: () => void
  /** Why Upload is disabled (the trial ended); the server refuses it anyway (AC-013-12). */
  uploadBlockedReason?: string
  /** Shown above every page, e.g. the trial banner. */
  banner?: ReactNode
  /** The top bar's page actions (the dashboard's period picker). */
  topbarExtra?: ReactNode
  /** The route the shell highlights; defaults to the location (previews and stories set it). */
  activePath?: string
}

export function AppShell({
  children,
  user,
  workspace,
  trial,
  counts,
  onUpload,
  onTour,
  uploadBlockedReason,
  banner,
  topbarExtra,
  activePath,
}: AppShellProps) {
  const { pathname } = useLocation()
  const path = activePath ?? pathname
  const chrome = chromeFor(path)

  return (
    <div className="viewport">
      <div className="app">
        <AppShellSide
          user={user}
          workspace={workspace}
          trial={trial}
          counts={counts}
          activePath={path}
        />
        <div className="main">
          <AppShellTopBar
            chrome={chrome}
            riskCount={counts?.risk}
            trial={trial}
            onUpload={onUpload}
            onTour={onTour}
            uploadBlockedReason={uploadBlockedReason}
            extra={topbarExtra}
          />
          <main id="content">
            {banner}
            {children}
          </main>
          <AppShellDock
            activePath={path}
            counts={counts}
            showFab={chrome.fab}
            onUpload={onUpload}
            uploadBlockedReason={uploadBlockedReason}
          />
        </div>
      </div>
    </div>
  )
}
