import { useTranslation } from 'react-i18next'
import { useAuth } from '../app/providers/useAuth'

export function DashboardPage() {
  const { t } = useTranslation('common')
  const { me, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Kredibel</h1>
          <p className="text-xs text-gray-500">
            Workspace: <span className="font-semibold text-emerald-700">{me?.orgId || 'None'}</span> ({me?.role || 'Guest'})
          </p>
        </div>
        <button
          onClick={() => signOut()}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          {t('auth.signOut')}
        </button>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Dashboard Empty State (AC-001-3) */}
        <div className="rounded-2xl border-2 border-dashed border-gray-300 p-12 text-center bg-white shadow-sm">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 mb-4">
            <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{t('dashboard.emptyTitle')}</h3>
          <p className="mt-2 text-sm text-gray-500 max-w-md mx-auto">
            {t('dashboard.emptyDescription')}
          </p>
          <div className="mt-6">
            <button
              type="button"
              className="inline-flex items-center rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-800"
            >
              {t('dashboard.uploadButton')}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
