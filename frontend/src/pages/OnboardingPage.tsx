import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../entities/session'
import { Button } from '../shared/ui/Button'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

type EntityType = 'INDIVIDUAL' | 'COMPANY'

const ENTITY_CHOICES: { value: EntityType; label: string; hint: string }[] = [
  { value: 'INDIVIDUAL', label: 'onboarding.individual', hint: 'onboarding.individualHint' },
  { value: 'COMPANY', label: 'onboarding.company', hint: 'onboarding.companyHint' },
]

/** AC-001-4 placeholder: the layout of the onboarding mock; spec 013 (T013-11) creates the workspace. */
export function OnboardingPage() {
  const { t } = useTranslation()
  const { signOut, user } = useAuth()
  const [entityType, setEntityType] = useState<EntityType>('COMPANY')

  return (
    <div className="min-h-screen flex flex-col expanded:flex-row bg-canvas">
      <AuthBrandPanel />

      <main className="flex-1 flex items-center justify-center p-4 medium:p-6 expanded:p-12 overflow-y-auto">
        <div className="w-full max-w-xl bg-surface p-8 rounded-md border border-line shadow-raised">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-ink">{t('onboarding.title')}</h1>
            <p className="mt-1 text-sm text-ink-muted">{t('onboarding.subtitle')}</p>
          </div>

          <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={t('onboarding.typeLabel')}>
            {ENTITY_CHOICES.map((choice) => {
              const selected = entityType === choice.value
              return (
                <button
                  key={choice.value}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setEntityType(choice.value)}
                  className={`p-4 rounded-xs border text-left transition-colors cursor-pointer ${
                    selected ? 'border-brand bg-brand-soft ring-1 ring-brand' : 'border-line bg-surface hover:bg-sunken'
                  }`}
                >
                  <div className="font-semibold text-sm text-ink mb-1">{t(choice.label)}</div>
                  <div className="text-xs text-ink-muted leading-relaxed">{t(choice.hint)}</div>
                </button>
              )
            })}
          </div>

          <div className="flex items-center justify-between pt-8">
            <button
              type="button"
              onClick={() => void signOut()}
              className="text-xs text-ink-muted hover:text-ink cursor-pointer"
            >
              {t('auth.signOutAs', { email: user?.email ?? '' })}
            </button>
            <Button type="button" variant="primary" size="lg" disabled>
              {t('onboarding.submit')}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
