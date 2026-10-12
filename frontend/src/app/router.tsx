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
import { DocumentPage } from '../pages/DocumentPage'
import { DocumentsPage } from '../pages/DocumentsPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OnboardingPage } from '../pages/OnboardingPage'
import { MonthPage } from '../pages/MonthPage'
import { MonthsPage } from '../pages/MonthsPage'
import {
  AssistantPage,
  CounterpartiesPage,
  LabelsPage,
  ReviewPage,
  RiskPage,
  RunsPage,
} from '../pages/Placeholders'
import { SettingsPage } from '../pages/SettingsPage'
import { AppShell, Button } from '../shared/ui'
import { OnboardingPreview } from './OnboardingPreview'
import { TrialBanner } from '../widgets/TrialBanner'
import { DocumentPreview, SettingsPreview, ShellPreview } from './ShellPreview'

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

function SessionError() {
  const { t } = useTranslation()
  const { refreshMe, signOut } = useAuth()
  return (
    <div className="viewport">
      <div className="page stack gap-4 items-start">
        <h1 className="type-h1">{t('session.errorTitle')}</h1>
        <p className="muted">{t('session.errorBody')}</p>
        <div className="row">
          <Button onClick={() => void refreshMe()}>{t('session.retry')}</Button>
          <Button variant="secondary" onClick={() => void signOut()}>
            {t('auth.signOut')}
          </Button>
        </div>
      </div>
    </div>
  )
}

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const { user, me, needsWorkspace, loading, meError } = useAuth()
  const navigate = useNavigate()
  const workspaceQuery = useWorkspace(Boolean(user && me?.orgId))

  if (loading) return <FullPageLoading />
  if (!user) return <Navigate to="/login" replace />
  if (meError) return <SessionError />
  if (needsWorkspace) return <Navigate to="/onboarding" replace />

  const name = me?.displayName || user.displayName || user.email || ''
  const shell = workspaceQuery.data
    ? shellPropsFromWorkspace(workspaceQuery.data, ({ entityType, currency, framework }) =>
        t('workspace.subtitle', {
          entity: t(`workspace.entity.${entityType}`),
          currency,
          framework,
        }),
      )
    : undefined
  return (
    <AppShell
      user={{ name, role: me?.role }}
      workspace={shell?.workspace}
      trial={shell?.trial}
      banner={shell?.trial && <TrialBanner trial={shell.trial} />}
      uploadBlockedReason={shell?.uploadBlocked ? t('shell.uploadBlocked') : undefined}
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

// docs/11 §4.2; P1 pages (assistant, labels, runs) show placeholders until their specs.
const PROTECTED_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/', element: <DashboardPage /> },
  { path: '/documents', element: <DocumentsPage /> },
  { path: '/documents/:docId', element: <DocumentPage /> },
  { path: '/months', element: <MonthsPage /> },
  { path: '/months/:month', element: <MonthPage /> },
  { path: '/review', element: <ReviewPage /> },
  { path: '/review/:itemId', element: <ReviewPage /> },
  { path: '/risk', element: <RiskPage /> },
  { path: '/risk/:findingId', element: <RiskPage /> },
  { path: '/counterparties', element: <CounterpartiesPage /> },
  { path: '/counterparties/:id', element: <CounterpartiesPage /> },
  { path: '/assistant', element: <AssistantPage /> },
  { path: '/assistant/:threadId', element: <AssistantPage /> },
  { path: '/labels', element: <LabelsPage /> },
  { path: '/labels/:labelId', element: <LabelsPage /> },
  { path: '/runs', element: <RunsPage /> },
  { path: '/runs/:runId', element: <RunsPage /> },
  { path: '/settings', element: <Navigate to="/settings/plan" replace /> },
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
      {import.meta.env.DEV && (
        <Route path="/preview/settings/:section" element={<SettingsPreview />} />
      )}
      {import.meta.env.DEV && <Route path="/preview/documents/:docId" element={<DocumentPreview />} />}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
