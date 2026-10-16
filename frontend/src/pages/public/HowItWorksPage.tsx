import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { useScrollProgress } from '../../shared/lib/useScrollProgress'
import { Icon, PageMeta } from '../../shared/ui'
import { PageHero } from '../../widgets/public/PageHero'
import { PaperArtefact } from '../../widgets/public/PaperArtefact'
import { PublicShell } from '../../widgets/PublicShell'

const STEPS = ['step1', 'step2', 'step3', 'step4', 'step5', 'step6', 'step7'] as const

const SHOTS: readonly { src: string; caption: string }[] = [
  { src: '/marketing/month.png', caption: 'shotMonth' },
  { src: '/marketing/evidence-viewer.png', caption: 'shotEvidence' },
  { src: '/marketing/review.png', caption: 'shotReview' },
  { src: '/marketing/dashboard.png', caption: 'shotDashboard' },
]

/**
 * How Kredibel works (spec 020 AC-020-6; docs/12 §12): the seven steps scroll past a sticky document
 * that changes with the step in view (stacked → copy held → two readings → ledger columns → the lamp
 * → ticks → the explanation), then the reading cost as a printed receipt and the real screens.
 */
export function HowItWorksPage() {
  const { t } = useTranslation('public')
  const stepsRef = useRef<HTMLOListElement>(null)
  const receiptRef = useRef<HTMLElement>(null)
  const galleryRef = useRef<HTMLDivElement>(null)
  const receiptView = useInViewAttr(receiptRef)
  const galleryView = useInViewAttr(galleryRef)
  const step = useScrollProgress(stepsRef, { offset: ['start center', 'end center'], chapters: STEPS.length })

  return (
    <PublicShell>
      <PageMeta title={t('meta.howTitle')} description={t('meta.howDescription')} path="/how-it-works" />
      <PageHero eyebrow={t('how.eyebrow')} title={t('how.title')} lead={t('how.lead')}>
        <div className="pub-actions">
          <Link className="button button-accent button-lg pub-cta" to="/login">
            {t('how.cta')}
          </Link>
        </div>
      </PageHero>

      <section className="pub-section pub-paper is-sheet pub-how" data-step={step}>
        <div className="pub-inner">
          <div className="pub-how-grid">
            <ol ref={stepsRef} className="pub-steps">
              {STEPS.map((key, i) => (
                <li className="pub-step" key={key} data-active={i === step}>
                  <div>
                    <h2>{t(`how.${key}Title`)}</h2>
                    <p>{t(`how.${key}Body`)}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="pub-how-aside" aria-hidden="true">
              <div className="pub-how-sticky">
                <div className="pub-how-doc">
                  <PaperArtefact kind="ledger" className="hd-back2" />
                  <PaperArtefact kind="invoice" className="hd-back" />
                  <PaperArtefact kind="statement" />
                  <i className="hd-layer is-a" />
                  <i className="hd-layer is-b" />
                  <i className="hd-cols" />
                  <i className="hd-lamp" />
                  <span className="hd-ticks">
                    <i />
                    <i />
                    <i />
                  </span>
                  <i className="hd-note" />
                </div>
              </div>
            </div>
          </div>

          <aside ref={receiptRef} className="pub-receipt" {...receiptView}>
            <h2>
              <Icon name="receipt" size="sm" />
              {t('how.costTitle')}
            </h2>
            <p>{t('how.costBody')}</p>
          </aside>

          <div ref={galleryRef} className="pub-gallery" {...galleryView}>
            {SHOTS.map((shot) => (
              <figure className="pub-shot" key={shot.src}>
                <img src={shot.src} alt="" loading="lazy" width={1440} height={900} />
                <figcaption>{t(`how.${shot.caption}`)}</figcaption>
              </figure>
            ))}
          </div>

          <div className="pub-end">
            <Link className="button button-primary button-lg" to="/login">
              {t('how.cta')}
            </Link>
          </div>
        </div>
      </section>
    </PublicShell>
  )
}
