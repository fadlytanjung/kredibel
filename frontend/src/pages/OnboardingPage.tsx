import { useTranslation } from 'react-i18next'
import { useAuth } from '../entities/session'
import { CreateWorkspaceForm, DemoChoice } from '../features/create-workspace'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

/** design/mocks/onboarding.html: the demo company when the server has one (spec 021), then one question
 * first, then the workspace and the free trial (AC-013-2). */
export function OnboardingPage() {
  const { t } = useTranslation('onboarding')
  const { me } = useAuth()

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
          {me?.demoAvailable && (
            <>
              <DemoChoice />
              <p className="onboard-or">{t('demo.or')}</p>
            </>
          )}
          <CreateWorkspaceForm />
        </section>
      </div>
    </div>
  )
}
