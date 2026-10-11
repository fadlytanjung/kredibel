import { useTranslation } from 'react-i18next'
import { CreateWorkspaceForm } from '../features/create-workspace'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

/** design/mocks/onboarding.html: one question first, then the workspace and the free trial (AC-013-2). */
export function OnboardingPage() {
  const { t } = useTranslation('onboarding')

  return (
    <div className="viewport">
      <div className="onboard">
        <AuthBrandPanel />
        <section className="onboard-form" aria-labelledby="ob-h">
          <div className="stack gap-2">
            <h1 className="type-title" id="ob-h">
              {t('title')}
            </h1>
            <p className="muted">{t('subtitle')}</p>
          </div>
          <CreateWorkspaceForm />
        </section>
      </div>
    </div>
  )
}
