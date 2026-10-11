/**
 * Brand column of the login and onboarding screens (design/mocks/onboarding.html).
 * The sample bank lines are illustration only and say so in the footnote.
 */

import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

function PromiseIcon({ children }: { children: ReactNode }) {
  return (
    <svg
      className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

const PROMISES = [
  {
    key: 'brand.promiseCopies',
    icon: (
      <>
        <rect x="8" y="8" width="12" height="12" rx="2" />
        <path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8" />
      </>
    ),
  },
  {
    key: 'brand.promiseReadTwice',
    icon: (
      <>
        <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
        <circle cx="12" cy="12" r="1" />
      </>
    ),
  },
  {
    key: 'brand.promiseAnyOrder',
    icon: (
      <>
        <path d="M4 7h11.5M12 3.5 15.5 7 12 10.5" />
        <path d="M20 17H8.5M12 13.5 8.5 17l3.5 3.5" />
      </>
    ),
  },
] as const

const SAMPLE_ROWS = [
  { date: 'outDate', text: 'outText', value: 'outAmount', muted: false },
  { date: 'inDate', text: 'inText', value: 'inAmount', muted: false },
  { date: 'copyDate', text: 'copyText', value: 'copyNote', muted: true },
] as const

export function AuthBrandPanel() {
  const { t } = useTranslation()

  // Mock: logo and tagline on top below 840 px; the full column with promises from 840 px.
  return (
    <section className="bg-inverse text-on-inverse px-4 pt-6 pb-8 flex flex-col gap-6 overflow-hidden expanded:w-1/2 expanded:px-16 expanded:py-10 expanded:justify-between">
      <div className="flex flex-col gap-6">
        <img
          src="/brand/kredibel-logo-on-dark.svg"
          alt={t('app.name')}
          className="h-9 w-auto self-start expanded:h-11"
        />
        <p className="text-3xl font-bold tracking-tight max-w-sm expanded:text-5xl">{t('brand.tagline')}</p>
        <ul className="hidden expanded:flex flex-col gap-3 text-sm text-on-inverse/85 max-w-md">
          {PROMISES.map((promise) => (
            <li key={promise.key} className="flex items-start gap-3">
              <PromiseIcon>{promise.icon}</PromiseIcon>
              <span>{t(promise.key)}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="hidden expanded:block font-mono text-sm" aria-label={t('brand.sampleLabel')}>
        {SAMPLE_ROWS.map((row) => (
          <div
            key={row.date}
            className="flex gap-4 items-baseline py-2.5 border-t border-on-inverse/15 last:border-b text-on-inverse/70"
          >
            <span>{t(`brand.sampleRows.${row.date}`)}</span>
            <span className="flex-1 min-w-0 truncate text-xs">{t(`brand.sampleRows.${row.text}`)}</span>
            <span className={row.muted ? 'text-xs font-semibold text-medium-line' : 'font-semibold text-on-inverse'}>
              {t(`brand.sampleRows.${row.value}`)}
            </span>
          </div>
        ))}
      </div>

      <p className="hidden expanded:block text-xs text-on-inverse/65 max-w-lg">{t('brand.footnote')}</p>
    </section>
  )
}
