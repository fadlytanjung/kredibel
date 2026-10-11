/**
 * Client router with authenticated and workspace-guarded routes.
 *
 * Normative references: docs/specs/001-foundation/spec.md AC-001-3, AC-001-4, and docs/11 §4.2.
 */

import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { shellPropsFromWorkspace, useWorkspace } from '../entities/workspace'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OnboardingPage } from '../pages/OnboardingPage'
import {
  AssistantPage,
  CounterpartiesPage,
  DocumentsPage,
  MonthsPage,
  ReviewPage,
  RiskPage,
  SettingsPage,
} from '../pages/Placeholders'
import { AppShell } from '../shared/ui'
import { OnboardingPreview } from './OnboardingPreview'
import { TrialBanner } from '../widgets/TrialBanner'
import { ShellPreview } from './ShellPreview'

function FullPageLoading() {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas">
      <div className="text-sm font-medium text-ink-muted" role="status">
        {t('common.loading')}
      </div>
    </div>
  )
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const { user, me, needsWorkspace, loading, signOut } = useAuth()
  const navigate = useNavigate()
  const workspaceQuery = useWorkspace(Boolean(user && me?.orgId))

  if (loading) return <FullPageLoading />
  if (!user) return <Navigate to="/login" replace />
  if (needsWorkspace) return <Navigate to="/onboarding" replace />

  const name = me?.displayName || user.displayName || user.email || ''
  const shell = workspaceQuery.data ? shellPropsFromWorkspace(workspaceQuery.data) : undefined
  return (
    <AppShell
      user={{ name, role: me?.role }}
      workspace={shell?.workspace}
      trial={shell?.trial}
      banner={shell?.trial && <TrialBanner trial={shell.trial} />}
      uploadBlockedReason={shell?.uploadBlocked ? t('shell.uploadBlocked') : undefined}
      onSignOut={() => void signOut()}
      onUpload={() => navigate('/documents?upload=1')}
    >
      {children}
    </AppShell>
  )
}

export function OnboardingRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <FullPageLoading />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

// docs/11 §4.2. P1 routes (labels, runs) arrive with specs 016 and 017.
const PROTECTED_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/', element: <DashboardPage /> },
  { path: '/documents', element: <DocumentsPage /> },
  { path: '/documents/:docId', element: <DocumentsPage /> },
  { path: '/months', element: <MonthsPage /> },
  { path: '/months/:month', element: <MonthsPage /> },
  { path: '/review', element: <ReviewPage /> },
  { path: '/review/:itemId', element: <ReviewPage /> },
  { path: '/risk', element: <RiskPage /> },
  { path: '/risk/:findingId', element: <RiskPage /> },
  { path: '/counterparties', element: <CounterpartiesPage /> },
  { path: '/counterparties/:id', element: <CounterpartiesPage /> },
  { path: '/assistant', element: <AssistantPage /> },
  { path: '/assistant/:threadId', element: <AssistantPage /> },
  { path: '/settings', element: <SettingsPage /> },
  { path: '/settings/:section', element: <SettingsPage /> },
]

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/onboarding"
        element={
          <OnboardingRoute>
            <OnboardingPage />
          </OnboardingRoute>
        }
      />
      {PROTECTED_ROUTES.map(({ path, element }) => (
        <Route key={path} path={path} element={<ProtectedRoute>{element}</ProtectedRoute>} />
      ))}
      {/* Visual regression target for the shell (tests/visual); never part of a production build. */}
      {import.meta.env.DEV && <Route path="/preview/shell" element={<ShellPreview />} />}
      {import.meta.env.DEV && <Route path="/preview/onboarding" element={<OnboardingPreview />} />}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
