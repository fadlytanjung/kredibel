/**
 * Client router with authenticated and workspace-guarded routes.
 *
 * Normative references: docs/specs/001-foundation/spec.md AC-001-3, AC-001-4, and docs/11 §4.2.
 */

import { Suspense, lazy, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useReviewItems } from '../entities/review'
import { useAuth } from '../entities/session'
import { shellPropsFromWorkspace, useWorkspace } from '../entities/workspace'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { CurrentMonthRedirect } from '../pages/CurrentMonthRedirect'
import { ContactPage } from '../pages/public/ContactPage'
import { FaqPage } from '../pages/public/FaqPage'
import { HowItWorksPage } from '../pages/public/HowItWorksPage'
import { LandingPage } from '../pages/public/LandingPage'
import { PricingPage } from '../pages/public/PricingPage'
import { PrivacyPage } from '../pages/public/PrivacyPage'
import { SecurityPage } from '../pages/public/SecurityPage'
import { TermsPage } from '../pages/public/TermsPage'
import { AppShell, type AppShellProps, Button } from '../shared/ui'
import { TourProvider, useTour } from '../features/tour'
import { TrialBanner } from '../widgets/TrialBanner'
import { useLabels } from '../entities/label'

// Every app page but the dashboard is its own chunk (AC-010-11): the first paint ships the shell only.
// The public pages load eagerly too: the landing is the first paint at `/` (spec 020).
const ProfitLossPage = lazy(() => import('../pages/ProfitLossPage').then((m) => ({ default: m.ProfitLossPage })))
const DocumentPage = lazy(() => import('../pages/DocumentPage').then((m) => ({ default: m.DocumentPage })))
const DocumentsPage = lazy(() => import('../pages/DocumentsPage').then((m) => ({ default: m.DocumentsPage })))
const OnboardingPage = lazy(() => import('../pages/OnboardingPage').then((m) => ({ default: m.OnboardingPage })))
const MonthPage = lazy(() => import('../pages/MonthPage').then((m) => ({ default: m.MonthPage })))
const MonthsPage = lazy(() => import('../pages/MonthsPage').then((m) => ({ default: m.MonthsPage })))
const AssistantPage = lazy(() => import('../pages/AssistantPage').then((m) => ({ default: m.AssistantPage })))
const ReviewPage = lazy(() => import('../pages/ReviewPage').then((m) => ({ default: m.ReviewPage })))
const RiskPage = lazy(() => import('../pages/RiskPage').then((m) => ({ default: m.RiskPage })))
const SettingsPage = lazy(() => import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const CounterpartiesPage = lazy(() => import('../pages/CounterpartiesPage').then((m) => ({ default: m.CounterpartiesPage })))
const CounterpartyPage = lazy(() => import('../pages/CounterpartyPage').then((m) => ({ default: m.CounterpartyPage })))
const LabelsPage = lazy(() => import('../pages/LabelsPage').then((m) => ({ default: m.LabelsPage })))
const RunsPage = lazy(() => import('../pages/RunsPage').then((m) => ({ default: m.RunsPage })))
const OnboardingPreview = lazy(() => import('./OnboardingPreview').then((m) => ({ default: m.OnboardingPreview })))
const AssistantPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.AssistantPreview })))
const DocumentPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.DocumentPreview })))
const DocumentsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.DocumentsPreview })))
const TourPreview = lazy(() => import('./TourPreview').then((m) => ({ default: m.TourPreview })))
const MonthPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.MonthPreview })))
const MonthsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.MonthsPreview })))
const ProfitLossPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.ProfitLossPreview })))
const CounterpartiesPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.CounterpartiesPreview })))
const CounterpartyPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.CounterpartyPreview })))
const RiskPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.RiskPreview })))
const LabelsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.LabelsPreview })))
const RunsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.RunsPreview })))
const ReviewPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.ReviewPreview })))
const SettingsPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.SettingsPreview })))
const ShellPreview = lazy(() => import('./ShellPreview').then((m) => ({ default: m.ShellPreview })))

const PREVIEW_ROUTES = import.meta.env.DEV || import.meta.env.VITE_PREVIEW_ROUTES === '1'

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
  const reviewQuery = useReviewItems(Boolean(user && me?.orgId))
  const labelsQuery = useLabels({ needsCheck: true, limit: 1 })

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
    <TourProvider role={me?.role} uid={me?.uid} workspaceName={workspaceQuery.data?.name}>
      <ShellWithTour
        user={{ name, role: me?.role }}
      counts={{ review: reviewQuery.data?.items.length, labels: labelsQuery.data?.summary.needsCheck }}
      workspace={shell?.workspace}
      trial={shell?.trial}
      banner={shell?.trial && <TrialBanner trial={shell.trial} />}
      uploadBlockedReason={shell?.uploadBlocked ? t('shell.uploadBlocked') : undefined}
      onUpload={() => navigate('/documents?upload=1')}
      >
        {/* The page chunk loads inside the shell, so the chrome never flashes away. */}
        <Suspense fallback={null}>{children}</Suspense>
      </ShellWithTour>
    </TourProvider>
  )
}

/** The shell with Take the tour wired to the tour around it (spec 021). */
function ShellWithTour(props: AppShellProps) {
  const tour = useTour()
  return <AppShell {...props} onTour={tour.start} />
}

export function OnboardingRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) return <FullPageLoading />
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

/** `/` is public: the landing for visitors, the dashboard for a signed-in user (spec 020, AC-020-1/9). */
export function IndexRoute() {
  const { user, loading } = useAuth()
  if (loading) return <FullPageLoading />
  if (user) return <Navigate to="/dashboard" replace />
  return <LandingPage />
}

// Public pages served by the same SPA (spec 020, AC-020-6).
const PUBLIC_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/pricing', element: <PricingPage /> },
  { path: '/how-it-works', element: <HowItWorksPage /> },
  { path: '/security', element: <SecurityPage /> },
  { path: '/faq', element: <FaqPage /> },
  { path: '/contact', element: <ContactPage /> },
  { path: '/privacy', element: <PrivacyPage /> },
  { path: '/terms', element: <TermsPage /> },
]

// docs/11 §4.2; the dashboard is at /dashboard so `/` can be the public landing (spec 020).
const PROTECTED_ROUTES: { path: string; element: ReactNode }[] = [
  { path: '/dashboard', element: <DashboardPage /> },
  { path: '/documents', element: <DocumentsPage /> },
  { path: '/documents/:docId', element: <DocumentPage /> },
  { path: '/months', element: <CurrentMonthRedirect /> },
  { path: '/months/all', element: <MonthsPage /> },
  { path: '/months/:month', element: <MonthPage /> },
  { path: '/review', element: <ReviewPage /> },
  { path: '/review/:itemId', element: <ReviewPage /> },
  { path: '/risk', element: <RiskPage /> },
  { path: '/risk/:findingId', element: <RiskPage /> },
  { path: '/counterparties', element: <CounterpartiesPage /> },
  { path: '/counterparties/:id', element: <CounterpartyPage /> },
  { path: '/profit-loss', element: <ProfitLossPage /> },
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
        {/* Visual regression targets (tests/visual) on synthetic fixtures; never part of a production
            build unless VITE_PREVIEW_ROUTES=1 asks for one to measure (Lighthouse, AC-010-11). */}
        {PREVIEW_ROUTES && <Route path="/preview/shell" element={<ShellPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/tour/*" element={<TourPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/onboarding" element={<OnboardingPreview />} />}
        {PREVIEW_ROUTES && (
          <Route path="/preview/settings/:section" element={<SettingsPreview />} />
        )}
        {PREVIEW_ROUTES && <Route path="/preview/documents" element={<DocumentsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/documents/:docId" element={<DocumentPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/months" element={<MonthsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/months/:month" element={<MonthPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/review" element={<ReviewPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/review/:itemId" element={<ReviewPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/risk" element={<RiskPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/risk/:findingId" element={<RiskPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/labels" element={<LabelsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/labels/:labelId" element={<LabelsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/runs" element={<RunsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/runs/:runId" element={<RunsPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/profit-loss" element={<ProfitLossPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/counterparties" element={<CounterpartiesPreview />} />}
        {PREVIEW_ROUTES && (
          <Route path="/preview/counterparties/:id" element={<CounterpartyPreview />} />
        )}
        {PREVIEW_ROUTES && <Route path="/preview/assistant" element={<AssistantPreview />} />}
        {PREVIEW_ROUTES && <Route path="/preview/assistant/:threadId" element={<AssistantPreview />} />}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
