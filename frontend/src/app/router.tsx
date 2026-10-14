/**
 * Client router with authenticated and workspace-guarded routes.
 *
 * Normative references: docs/specs/001-foundation/spec.md AC-001-3, AC-001-4, and docs/11 §4.2.
 */

import { lazy, Suspense, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { shellPropsFromWorkspace, useWorkspace } from '../entities/workspace'
import { NotFoundPage } from '../pages/NotFoundPage'
import { ContactPage } from '../pages/public/ContactPage'
import { FaqPage } from '../pages/public/FaqPage'
import { HowItWorksPage } from '../pages/public/HowItWorksPage'
import { LandingPage } from '../pages/public/LandingPage'
import { PricingPage } from '../pages/public/PricingPage'
import { PrivacyPage } from '../pages/public/PrivacyPage'
import { SecurityPage } from '../pages/public/SecurityPage'
import { TermsPage } from '../pages/public/TermsPage'
import { AppShell, Button } from '../shared/ui'
import { TrialBanner } from '../widgets/TrialBanner'

// The public pages load eagerly (the landing is the first paint); the signed-in app, Login and
// Onboarding are split out of the first load (spec 018, T018-19; docs/11 performance budget).
const DashboardPage = lazy(() => import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const DocumentPage = lazy(() => import('../pages/DocumentPage').then((m) => ({ default: m.DocumentPage })))
const DocumentsPage = lazy(() => import('../pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage })))
const LoginPage = lazy(() => import('../pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const OnboardingPage = lazy(() =>
  import('../pages/OnboardingPage').then((m) => ({ default: m.OnboardingPage })),
)
const SettingsPage = lazy(() => import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const placeholder = (name: keyof typeof import('../pages/Placeholders')) =>
  lazy(() => import('../pages/Placeholders').then((m) => ({ default: m[name] })))
const AssistantPage = placeholder('AssistantPage')
const CounterpartiesPage = placeholder('CounterpartiesPage')
const LabelsPage = placeholder('LabelsPage')
const MonthsPage = placeholder('MonthsPage')
const ReviewPage = placeholder('ReviewPage')
const RiskPage = placeholder('RiskPage')
const RunsPage = placeholder('RunsPage')
const OnboardingPreview = lazy(() =>
  import('./OnboardingPreview').then((m) => ({ default: m.OnboardingPreview })),
)
const ShellPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.ShellPreview })))
const SettingsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.SettingsPreview })))

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
      {/* The page chunk loads inside the shell, so the chrome never flashes away. */}
      <Suspense fallback={null}>{children}</Suspense>
    </AppShell>
  )
}

export function OnboardingRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <FullPageLoading />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

/** `/` is public: the landing for visitors, the dashboard for a signed-in user (spec 018, AC-018-1/9). */
export function IndexRoute() {
  const { user, loading } = useAuth()
  if (loading) return <FullPageLoading />
  if (user) return <Navigate to="/dashboard" replace />
  return <LandingPage />
}

// Public pages served by the same SPA (spec 018, AC-018-6).
const PUBLIC_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/pricing', element: <PricingPage /> },
  { path: '/how-it-works', element: <HowItWorksPage /> },
  { path: '/security', element: <SecurityPage /> },
  { path: '/faq', element: <FaqPage /> },
  { path: '/contact', element: <ContactPage /> },
  { path: '/privacy', element: <PrivacyPage /> },
  { path: '/terms', element: <TermsPage /> },
]

// docs/11 §4.2; the dashboard is at /dashboard so `/` can be the public landing; P1 pages
// (assistant, labels, runs) show placeholders until their specs.
const PROTECTED_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/dashboard', element: <DashboardPage /> },
  { path: '/documents', element: <DocumentsPage /> },
  { path: '/documents/:docId', element: <DocumentPage /> },
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
  { path: '/labels', element: <LabelsPage /> },
  { path: '/labels/:labelId', element: <LabelsPage /> },
  { path: '/runs', element: <RunsPage /> },
  { path: '/runs/:runId', element: <RunsPage /> },
  { path: '/settings', element: <Navigate to="/settings/plan" replace /> },
  { path: '/settings/:section', element: <SettingsPage /> },
]

export function AppRouter() {
  return (
    <Suspense fallback={<FullPageLoading />}>
      <Routes>
        <Route path="/" element={<IndexRoute />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/onboarding"
          element={
            <OnboardingRoute>
              <OnboardingPage />
            </OnboardingRoute>
          }
        />
        {PUBLIC_ROUTES.map(({ path, element }) => (
          <Route key={path} path={path} element={element} />
        ))}
        {PROTECTED_ROUTES.map(({ path, element }) => (
          <Route key={path} path={path} element={<ProtectedRoute>{element}</ProtectedRoute>} />
        ))}
        {/* Visual regression target for the shell (tests/visual); never part of a production build. */}
        {import.meta.env.DEV && <Route path="/preview/shell" element={<ShellPreview />} />}
        {import.meta.env.DEV && <Route path="/preview/onboarding" element={<OnboardingPreview />} />}
        {import.meta.env.DEV && (
          <Route path="/preview/settings/:section" element={<SettingsPreview />} />
        )}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
