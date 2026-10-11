import { useTranslation } from 'react-i18next'
import { useAuth } from '../app/providers/useAuth'

export function OnboardingPage() {
  const { t } = useTranslation('common')
  const { signOut, user } = useAuth()

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-lg rounded-xl bg-white p-8 border border-gray-200 shadow-sm text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-800 mb-4 font-bold text-xl">
          1
        </div>
        <h2 className="text-2xl font-bold text-gray-900">{t('onboarding.title')}</h2>
        <p className="mt-2 text-sm text-gray-600">{t('onboarding.subtitle')}</p>

        <div className="mt-8 p-4 bg-gray-50 rounded-lg border border-gray-200 text-left text-sm text-gray-700">
          <p className="font-semibold text-gray-900">Signed in as:</p>
          <p className="font-mono text-xs mt-1 text-gray-600">{user?.email}</p>
          <p className="mt-4 text-xs text-gray-500">
            Workspace onboarding form will arrive in Spec 013 (Workspace & Plans).
          </p>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={() => signOut()}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t('auth.signOut')}
          </button>
        </div>
      </div>
    </div>
  )
}
