/**
 * Settings → Plan and usage (design/mocks/plan-usage.html, docs/11 §6.9, AC-013-11): the trial
 * hero with its 30-cell track, usage meters that warn at 80%, the plan cards and the coming-soon
 * features. Nothing here can start a payment.
 */

import { useTranslation } from 'react-i18next'
import type { PlanCatalog } from '../entities/plan'
import type { Workspace } from '../entities/workspace'
import { Badge } from '../shared/ui/Badge'
import { Icon, type IconName } from '../shared/ui/Icon'
import { formatDate } from '../shared/lib/formatDate'
import { formatMoney } from '../shared/lib/formatMoney'

const NEAR = 0.8

const FEATURE_ICONS: Record<string, IconName> = {
  loan_readiness_report: 'book',
  bank_feeds: 'bank',
}

interface MeterSpec {
  key: 'documents' | 'pages' | 'ai' | 'runs' | 'seats' | 'assistant'
  used: number
  max: number
  usedText: string
  maxText: string
  note: string
}

function Meter({ meter, near }: { meter: MeterSpec; near: boolean }) {
  const { t } = useTranslation('settings')
  const percent = meter.max > 0 ? Math.min(100, Math.round((meter.used / meter.max) * 100)) : 0
  return (
    <div className={`meter${near ? ' is-near' : ''}`}>
      <div className="m-top">
        <span>{t(`plan.meters.${meter.key}`)}</span>
        <strong>
          {meter.usedText} <small>{t('plan.of', { max: meter.maxText })}</small>
        </strong>
      </div>
      <div
        className="meter-bar"
        role="meter"
        aria-label={t(`plan.meters.${meter.key}`)}
        aria-valuemin={0}
        aria-valuemax={meter.max}
        aria-valuenow={meter.used}
      >
        <i style={{ width: `${percent}%` }} /* allow-raw-style: computed meter width */ />
      </div>
      {meter.note && <p className="m-note">{meter.note}</p>}
    </div>
  )
}

export function PlanAndUsage({ workspace, catalog }: { workspace: Workspace; catalog: PlanCatalog }) {
  const { t } = useTranslation('settings')
  const sub = workspace.subscription
  const limits = sub.limits ?? {}
  const usage = workspace.usage ?? {}
  const plan = catalog.plans.find((p) => p.id === sub.planId)
  const trialDays = plan?.trialDays ?? 30
  const daysLeft = sub.trialDaysLeft ?? 0
  const expired = sub.status === 'TRIAL_EXPIRED'
  const dayOfTrial = Math.min(trialDays, Math.max(0, trialDays - daysLeft))
  const endDate = sub.trialEndsAt ? formatDate(sub.trialEndsAt) : ''

  const n = (value: number | string | undefined) => Number(value ?? 0)
  const usd = (value: string | number | undefined) =>
    formatMoney(String(value ?? '0'), { currency: 'USD', code: true, fractionDigits: 2 })
  const pagesLeft = Math.max(0, n(limits.extractedPagesPerMonth) - n(usage.extractedPages))
  const runsNear = n(usage.monthRunsToday) >= NEAR * n(limits.monthRunsPerDay)

  const meters: MeterSpec[] = [
    {
      key: 'documents',
      used: n(usage.documentsUploaded),
      max: n(limits.documentsPerMonth),
      usedText: String(n(usage.documentsUploaded)),
      maxText: String(n(limits.documentsPerMonth)),
      note: t('plan.notes.documents'),
    },
    {
      key: 'pages',
      used: n(usage.extractedPages),
      max: n(limits.extractedPagesPerMonth),
      usedText: String(n(usage.extractedPages)),
      maxText: String(n(limits.extractedPagesPerMonth)),
      note: t('plan.notes.pages', { left: pagesLeft }),
    },
    {
      key: 'ai',
      used: n(usage.aiSpendUsd),
      max: n(limits.aiSpendUsdPerMonth),
      usedText: usd(usage.aiSpendUsd),
      maxText: usd(limits.aiSpendUsdPerMonth),
      note: t('plan.notes.ai'),
    },
    {
      key: 'runs',
      used: n(usage.monthRunsToday),
      max: n(limits.monthRunsPerDay),
      usedText: String(n(usage.monthRunsToday)),
      maxText: String(n(limits.monthRunsPerDay)),
      note: runsNear ? t('plan.notes.runsNear') : t('plan.notes.runs'),
    },
    {
      key: 'seats',
      used: n(usage.seatsUsed),
      max: n(limits.seats),
      usedText: String(n(usage.seatsUsed)),
      maxText: String(n(limits.seats)),
      note: t('plan.notes.seats'),
    },
    {
      key: 'assistant',
      used: n(usage.assistantQuestionsToday),
      max: n(limits.assistantQuestionsPerDay),
      usedText: String(n(usage.assistantQuestionsToday)),
      maxText: String(n(limits.assistantQuestionsPerDay)),
      note: t('plan.notes.assistant'),
    },
  ]

  return (
    <div className="stack gap-8">
      <section className="trial-hero" aria-labelledby="trial-h">
        <div>
          <p className="days num" id="trial-h">
            {daysLeft}
            <small>{t('plan.daysLeft')}</small>
          </p>
        </div>
        <div className="stack gap-3">
          <p>{expired ? t('plan.endedOn', { date: endDate }) : t('plan.endsOn', { date: endDate })}</p>
          <div
            className="trial-track"
            role="img"
            aria-label={t('plan.track', { day: dayOfTrial, days: trialDays })}
          >
            {Array.from({ length: trialDays }, (_, day) => (
              <i key={day} className={day < dayOfTrial ? 'used' : undefined} />
            ))}
          </div>
        </div>
      </section>

      <section aria-labelledby="use-h" className="meters-wrap" id="usage">
        <div className="section-head">
          <h2 className="type-h2" id="use-h">
            {t('plan.usage')}
          </h2>
          <p>{t('plan.usageNote')}</p>
        </div>
        <div className="meters">
          {meters.map((meter) => {
            const near = meter.max > 0 && meter.used >= NEAR * meter.max
            const shown = near && meter.key !== 'runs' ? { ...meter, note: t('plan.notes.near') } : meter
            return <Meter key={meter.key} meter={shown} near={near} />
          })}
        </div>
      </section>

      <section aria-labelledby="plans-h" className="plans-wrap stack gap-4">
        <div className="section-head">
          <h2 className="type-h2" id="plans-h">
            {t('plan.plans')}
          </h2>
          <p>{t('plan.plansNote')}</p>
        </div>
        <div className="plans">
          {catalog.plans.map((item) => {
            const current = item.id === sub.planId
            return (
              <div key={item.id} className={`plan ${current ? 'is-current' : 'is-soon'}`}>
                <div className="plan-head">
                  {current ? (
                    <Badge variant="brand">{t('plan.yourPlan')}</Badge>
                  ) : (
                    <Badge variant="outline">{t('plan.comingSoon')}</Badge>
                  )}
                  <h3>{item.label}</h3>
                  {item.priceLabel && <p className="muted small">{item.priceLabel}</p>}
                </div>
                <ul>
                  {item.highlights.map((line) => (
                    <li key={line}>
                      <Icon name="check" size="sm" />
                      {line}
                    </li>
                  ))}
                </ul>
                <div className="plan-foot">
                  {current ? (
                    <a className="button button-secondary button-block" href="#usage">
                      {t('plan.seeLimits')}
                    </a>
                  ) : (
                    <button type="button" className="button button-block" disabled>
                      {t('plan.notAvailable')}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <div className="soon-features">
          {(catalog.comingSoonFeatures ?? []).map((feature) => (
            <div key={feature.id} className="soon">
              <span className="ico">
                <Icon name={FEATURE_ICONS[feature.id] ?? 'sparkles'} />
              </span>
              <div>
                <div className="row">
                  <h3>{feature.label}</h3>
                  <Badge variant="outline">{t('plan.comingSoon')}</Badge>
                </div>
                {feature.description && <p>{feature.description}</p>}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
