import { useTranslation } from 'react-i18next'
import { CreateWorkspaceForm } from '../features/create-workspace'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

/** docs/11 §6.1: one question first, then the workspace and the free trial (AC-013-2). */
export function OnboardingPage() {
  const { t } = useTranslation('onboarding')

  return (
    <div className="min-h-screen flex flex-col expanded:flex-row bg-canvas">
      <AuthBrandPanel />

      <main className="flex-1 flex items-center justify-center p-4 medium:p-6 expanded:p-12 overflow-y-auto">
        <div className="w-full max-w-xl bg-surface p-6 medium:p-8 rounded-md border border-line shadow-raised">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-ink">{t('title')}</h1>
            <p className="mt-1 text-sm text-ink-muted">{t('subtitle')}</p>
          </div>
          <CreateWorkspaceForm />
        </div>
      </main>
    </div>
  )
}
