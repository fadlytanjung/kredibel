import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { usePointerTilt } from '../../shared/lib/usePointerTilt'
import { Icon, PageMeta } from '../../shared/ui'
import { PageHero } from '../../widgets/public/PageHero'
import { PublicShell } from '../../widgets/PublicShell'

const PLAN_KEYS = ['starter', 'professional', 'enterprise'] as const
const HIGHLIGHT_KEYS = ['1', '2', '3'] as const

/**
 * Pricing / Plans (spec 020 AC-020-5; docs/12 §12). Static copy mirroring contracts/plans.v1.yaml:
 * the free trial is available — lifted forward, tilting toward the pointer — and the paid tiers are
 * frosted further back, coming soon with no price. It does not call GET /api/plans, which needs a
 * token.
 */
export function PricingPage() {
  const { t } = useTranslation('public')
  const plansRef = useRef<HTMLDivElement>(null)
  const trialRef = useRef<HTMLElement>(null)
  const plansView = useInViewAttr(plansRef)
  usePointerTilt(trialRef)

  return (
    <PublicShell>
      <PageMeta title={t('meta.pricingTitle')} description={t('meta.pricingDescription')} path="/pricing" />
      <PageHero eyebrow={t('pricing.eyebrow')} title={t('pricing.title')} lead={t('pricing.lead')} />

      <section className="pub-section pub-paper is-sheet">
        <div className="pub-inner">
          <div ref={plansRef} className="pub-plans" {...plansView}>
            <article ref={trialRef} className="pub-plan is-current">
              <div className="pub-plan-head">
                <span className="badge badge-brand">{t('pricing.available')}</span>
                <h2>{t('pricing.freeLabel')}</h2>
                <p className="pub-plan-price">{t('pricing.freePrice')}</p>
              </div>
              <ul>
                {HIGHLIGHT_KEYS.map((n) => (
                  <li key={n}>
                    <Icon name="check" size="sm" />
                    <span>{t(`pricing.freeHighlight${n}`)}</span>
                  </li>
                ))}
              </ul>
              <div className="pub-plan-foot">
                <Link className="button button-accent button-lg button-block pub-cta" to="/login">
                  {t('pricing.cta')}
                </Link>
              </div>
            </article>
            {PLAN_KEYS.map((plan) => (
              <article className="pub-plan is-soon" key={plan}>
                <div className="pub-plan-head">
                  <span className="badge badge-outline">{t('pricing.comingSoon')}</span>
                  <h2>{t(`pricing.${plan}`)}</h2>
                  <p className="pub-muted">
                    {plan === 'enterprise' ? t('pricing.noPriceEnterprise') : t('pricing.noPrice')}
                  </p>
                </div>
                <ul>
                  {HIGHLIGHT_KEYS.map((n) => (
                    <li key={n}>
                      <Icon name="check" size="sm" />
                      <span>{t(`pricing.${plan}Highlight${n}`)}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>

          <div className="pub-block">
            <h2 className="pub-h3">{t('pricing.comingSoonFeatures')}</h2>
            <div className="pub-soon-grid">
              <div className="pub-soon">
                <span className="ico">
                  <Icon name="file-text" />
                </span>
                <div>
                  <h3>{t('pricing.loanReadiness')}</h3>
                  <p>{t('pricing.loanReadinessBody')}</p>
                </div>
              </div>
              <div className="pub-soon">
                <span className="ico">
                  <Icon name="bank" />
                </span>
                <div>
                  <h3>{t('pricing.bankFeeds')}</h3>
                  <p>{t('pricing.bankFeedsBody')}</p>
                </div>
              </div>
            </div>
          </div>

          <p className="pub-note">
            <Icon name="lock" size="sm" />
            <span>{t('pricing.note')}</span>
          </p>
          <p className="pub-note">
            {t('pricing.questions')}{' '}
            <Link className="link" to="/contact">
              {t('pricing.contactLink')}
            </Link>
          </p>
        </div>
      </section>
    </PublicShell>
  )
}
