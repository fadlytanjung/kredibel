import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { PageMeta } from '../../shared/ui'
import { PageHero } from '../../widgets/public/PageHero'
import { PublicShell } from '../../widgets/PublicShell'

const BLOCKS = [
  { title: 'docsTitle', body: 'docsBody' },
  { title: 'readingsTitle', body: 'readingsBody' },
  { title: 'evidenceTitle', body: 'evidenceBody' },
  { title: 'humanTitle', body: 'peopleBody' },
  { title: 'dataTitle', body: 'dataBody' },
  { title: 'cloudTitle', body: 'cloudBody' },
  { title: 'limitsTitle', body: 'limitsBody' },
] as const

/**
 * Security and trust (spec 020 AC-020-6, AC-020-7; docs/12 §12): a seal that draws itself, then the
 * product's seven honesty rules as plates in a vault, flipping up in turn.
 */
export function SecurityPage() {
  const { t } = useTranslation('public')
  const vaultRef = useRef<HTMLOListElement>(null)
  const vaultView = useInViewAttr(vaultRef)

  return (
    <PublicShell>
      <PageMeta title={t('meta.securityTitle')} description={t('meta.securityDescription')} />
      <PageHero
        eyebrow={t('security.eyebrow')}
        title={t('security.title')}
        lead={t('security.lead')}
        art={
          <svg className="pub-seal" viewBox="0 0 200 200" focusable="false">
            <circle className="ring" cx={100} cy={100} r={94} pathLength={1} />
            <circle className="orbit" cx={100} cy={100} r={80} pathLength={1} />
            <circle className="ring2" cx={100} cy={100} r={64} pathLength={1} />
            <path className="tick" d="M 70 102 L 92 124 L 134 78" pathLength={1} />
          </svg>
        }
      />

      <section className="pub-section pub-paper is-sheet">
        <div className="pub-inner">
          <ol ref={vaultRef} className="pub-vault" {...vaultView}>
            {BLOCKS.map((block) => (
              <li key={block.title}>
                <h2>{t(`security.${block.title}`)}</h2>
                <p>{t(`security.${block.body}`)}</p>
              </li>
            ))}
          </ol>
          <div className="pub-links">
            <Link className="button button-secondary button-lg" to="/privacy">
              {t('security.privacy')}
            </Link>
            <Link className="button button-secondary button-lg" to="/terms">
              {t('security.terms')}
            </Link>
          </div>
        </div>
      </section>
    </PublicShell>
  )
}
