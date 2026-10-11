/**
 * Responsive app shell: sidebar from 1200 px, rail from 600 px, bottom navigation below
 * (docs/11 §4.1, docs/12 §5, AC-001-16). Presentational: everything it shows comes in as props.
 */

import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { useSizeClass } from '../lib/useSizeClass'
import { AppShellCompactNav } from './AppShellCompactNav'
import { AppShellRail } from './AppShellRail'
import { AppShellSidebar } from './AppShellSidebar'
import { AppShellTopBar } from './AppShellTopBar'
import {
  currentNavItem,
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
  onSignOut?: () => void
  onUpload?: () => void
  /** Why Upload is disabled (the trial ended); the server refuses it anyway (AC-013-12). */
  uploadBlockedReason?: string
  /** Shown above every page, e.g. the trial banner. */
  banner?: ReactNode
}

export function AppShell({
  children,
  user,
  workspace,
  trial,
  counts,
  onSignOut,
  onUpload,
  uploadBlockedReason,
  banner,
}: AppShellProps) {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const { isCompact, isLarge, isWide } = useSizeClass()
  const showSidebar = isLarge || isWide
  const showRail = !isCompact && !showSidebar
  const current = currentNavItem(pathname)

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col medium:flex-row">
      {showSidebar && (
        <AppShellSidebar
          user={user}
          workspace={workspace}
          trial={trial}
          counts={counts}
          onSignOut={onSignOut}
        />
      )}
      {showRail && <AppShellRail user={user} counts={counts} />}

      <div className="flex-1 flex flex-col min-w-0">
        <AppShellTopBar
          compact={isCompact}
          title={current ? t(`nav.${current.key}.long`) : ''}
          riskCount={counts?.risk}
          trial={trial}
          onUpload={onUpload}
          uploadBlockedReason={uploadBlockedReason}
        />
        <main
          id="content"
          className="flex-1 px-4 medium:px-6 large:px-8 py-5 medium:py-6 large:py-8 max-w-7xl w-full"
        >
          {banner}
          {children}
        </main>
      </div>

      {isCompact && (
        <AppShellCompactNav
          user={user}
          workspace={workspace}
          counts={counts}
          onSignOut={onSignOut}
          onUpload={onUpload}
          uploadBlockedReason={uploadBlockedReason}
        />
      )}
    </div>
  )
}
