import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <div className="text-center">
        <p className="text-6xl font-extrabold text-brand">{t('notFound.code')}</p>
        <h1 className="mt-4 text-xl font-semibold text-ink">{t('notFound.title')}</h1>
        <p className="mt-2 text-sm text-ink-muted">{t('notFound.body')}</p>
        <Link
          to="/"
          className="inline-block mt-6 rounded-sm bg-brand px-4 py-2 text-sm font-semibold text-on-brand shadow-xs hover:bg-brand-hover"
        >
          {t('notFound.backToDashboard')}
        </Link>
      </div>
    </div>
  )
}
