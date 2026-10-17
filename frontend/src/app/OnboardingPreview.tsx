/**
 * Dev-only onboarding page with a stub session, for the Playwright visual tests (AC-001-17).
 * Not routed in production builds.
 */

import { AuthContext, type AuthContextType } from '../entities/session'
import { OnboardingPage } from '../pages/OnboardingPage'
import { WelcomePage } from '../pages/WelcomePage'

const PREVIEW_SESSION = {
  user: { email: 'owner@example.test' },
  me: null,
  loading: false,
  needsWorkspace: true,
  refreshSession: async () => null,
  signOut: async () => undefined,
} as unknown as AuthContextType

export function OnboardingPreview() {
  // ?demo=1: the server has a demo template (spec 021); opening it signs the preview in.
  const demo = new URLSearchParams(window.location.search).get('demo') === '1'
  const session = demo
    ? ({
        ...PREVIEW_SESSION,
        me: { uid: 'u_new', orgId: null, needsWorkspace: true, demoAvailable: true },
        refreshSession: async () => ({ uid: 'u_new', orgId: 'org_demo_copy', needsWorkspace: false, demoAvailable: true }),
      } as unknown as AuthContextType)
    : PREVIEW_SESSION
  return (
    <AuthContext.Provider value={session}>
      <OnboardingPage />
    </AuthContext.Provider>
  )
}

/** Spec 024: the welcome question; the browser tests serve /api/workspace. */
export function WelcomePreview() {
  return <WelcomePage />
}
