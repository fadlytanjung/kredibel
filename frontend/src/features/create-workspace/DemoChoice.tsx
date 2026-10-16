/**
 * The demo company on onboarding (spec 021, AC-021-1, AC-021-3; mock onboarding.html): open a copy
 * of Sunrise Coffee Roasters' books, already read and reconciled, then take the guided tour.
 */

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { ProblemError } from '../../shared/api/client'
import { Icon } from '../../shared/ui'
import { useOpenDemo } from './useOpenDemo'

export function DemoChoice() {
  const { t } = useTranslation(['onboarding', 'errors'])
  const navigate = useNavigate()
  const demo = useOpenDemo()
  useEffect(() => {
    if (demo.phase === 'done') navigate('/dashboard?tour=1', { replace: true })
  }, [demo.phase, navigate])
  const busy = demo.phase === 'creating' || demo.phase === 'finishing'
  const error = demo.error instanceof ProblemError ? t(`errors:${demo.error.code}`, { defaultValue: demo.error.message }) : demo.error ? t('errors:fallback') : null

  return (
    <section className="onboard-demo" aria-labelledby="demo-h">
      <Icon name="sparkles" />
      <div className="stack gap-1">
        <h2 id="demo-h">{t('demo.title')}</h2>
        <p>{t('demo.body')}</p>
      </div>
      <div className="actions">
        <button type="button" className="button button-secondary" disabled={busy} onClick={() => demo.mutate()}>
          {t(busy ? 'demo.opening' : 'demo.open')}
        </button>
        {demo.phase === 'notReady' && <span className="small muted">{t('notReady')}</span>}
        {error && (
          <span className="small status-line bad" role="alert">
            {error}
          </span>
        )}
      </div>
    </section>
  )
}
