/**
 * Plan limits from the server (docs/11 §7a, AC-013-13): a 403 PLAN_LIMIT_REACHED anywhere opens
 * this dialog with the limit, the usage and the maximum; TRIAL_EXPIRED refreshes the workspace so
 * the trial banner and the disabled Upload appear at once.
 */

import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { setProblemListener, type ProblemError } from '../../shared/api/client'
import { Icon } from '../../shared/ui/Icon'

interface LimitProblem {
  limit?: string
  used?: number | string
  max?: number | string
}

export function PlanLimitDialog({ problem, onClose }: { problem: LimitProblem; onClose: () => void }) {
  const { t } = useTranslation()
  const closeRef = useRef<HTMLButtonElement>(null)
  const what = t(`planLimit.limits.${problem.limit ?? ''}`, { defaultValue: problem.limit ?? '' })

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <button type="button" className="absolute inset-0 border-0 bg-inverse/40" aria-label={t('planLimit.close')} onClick={onClose} />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="plan-limit-title"
        aria-describedby="plan-limit-body"
        className="panel panel-pad relative stack gap-4 w-full max-w-md shadow-overlay"
      >
        <span className="grid place-items-center w-11 h-11 rounded-md bg-medium-soft text-medium">
          <Icon name="gauge" />
        </span>
        <h2 className="type-h2" id="plan-limit-title">
          {t('planLimit.title')}
        </h2>
        <p id="plan-limit-body" className="muted">
          {problem.used !== undefined && problem.max !== undefined
            ? t('planLimit.body', { used: problem.used, max: problem.max, what })
            : t('planLimit.bodyNoNumbers', { what })}
        </p>
        <div className="row">
          <Link className="button button-primary" to="/settings/plan" onClick={onClose}>
            {t('planLimit.planAndUsage')}
          </Link>
          <button ref={closeRef} type="button" className="button button-secondary" onClick={onClose}>
            {t('planLimit.close')}
          </button>
        </div>
      </div>
    </div>
  )
}

export function PlanLimitProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [problem, setProblem] = useState<LimitProblem | null>(null)

  useEffect(() => {
    setProblemListener((error: ProblemError) => {
      if (error.code === 'PLAN_LIMIT_REACHED') {
        setProblem(error.problem as LimitProblem)
        void queryClient.invalidateQueries({ queryKey: ['workspace'] })
      } else if (error.code === 'TRIAL_EXPIRED') {
        void queryClient.invalidateQueries({ queryKey: ['workspace'] })
      }
    })
    return () => setProblemListener(null)
  }, [queryClient])

  return (
    <>
      {children}
      {problem && <PlanLimitDialog problem={problem} onClose={() => setProblem(null)} />}
    </>
  )
}
