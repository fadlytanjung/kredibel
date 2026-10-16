import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { PageMeta } from '../../shared/ui'
import { PageHero } from '../../widgets/public/PageHero'
import { PublicShell } from '../../widgets/PublicShell'

const QA = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const

/**
 * FAQ (spec 020 AC-020-6; docs/12 §12): nine native disclosures that open smoothly, beside a sticky
 * way to ask the rest.
 */
export function FaqPage() {
  const { t } = useTranslation('public')

  return (
    <PublicShell>
      <PageMeta title={t('meta.faqTitle')} description={t('meta.faqDescription')} path="/faq" />
      <PageHero eyebrow={t('faq.eyebrow')} title={t('faq.title')} lead={t('faq.lead')} />

      <section className="pub-section pub-paper is-sheet">
        <div className="pub-inner pub-faq-grid">
          <aside className="pub-faq-aside">
            <p className="pub-faq-count" aria-hidden="true">
              {QA.length}
            </p>
            <p className="pub-lead">{t('faq.more')}</p>
            <Link className="button button-primary button-lg" to="/contact">
              {t('faq.contactLink')}
            </Link>
          </aside>
          <div className="pub-faq">
            {QA.map((n) => (
              <details key={n}>
                <summary>
                  <span>{t(`faq.q${n}`)}</span>
                  <span className="pub-faq-sign" aria-hidden="true" />
                </summary>
                <p>{t(`faq.a${n}`)}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </PublicShell>
  )
}
