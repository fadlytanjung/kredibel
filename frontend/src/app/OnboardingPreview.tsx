/**
 * Dev-only onboarding page with a stub session, for the Playwright visual tests (AC-001-17).
 * Not routed in production builds.
 */

import { AuthContext, type AuthContextType } from '../entities/session'
import { OnboardingPage } from '../pages/OnboardingPage'

const PREVIEW_SESSION = {
  user: { email: 'owner@example.test' },
  me: null,
  loading: false,
  needsWorkspace: true,
  refreshSession: async () => null,
  signOut: async () => undefined,
} as unknown as AuthContextType

export function OnboardingPreview() {
  return (
    <AuthContext.Provider value={PREVIEW_SESSION}>
      <OnboardingPage />
    </AuthContext.Provider>
  )
}
