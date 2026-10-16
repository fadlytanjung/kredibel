import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { usePointerTilt } from '../../shared/lib/usePointerTilt'
import { Icon, PageMeta } from '../../shared/ui'
import { CopyEmailButton } from '../../widgets/public/CopyEmailButton'
import { PageHero } from '../../widgets/public/PageHero'
import { PublicShell } from '../../widgets/PublicShell'

/**
 * Contact (spec 020 AC-020-7; docs/12 §12): a real mailbox on a letter that tilts toward the pointer,
 * a button to copy the address, and no backend form.
 */
export function ContactPage() {
  const { t } = useTranslation('public')
  const letterRef = useRef<HTMLDivElement>(null)
  usePointerTilt(letterRef)

  return (
    <PublicShell>
      <PageMeta title={t('meta.contactTitle')} description={t('meta.contactDescription')} path="/contact" />
      <PageHero eyebrow={t('contact.eyebrow')} title={t('contact.title')} lead={t('contact.lead')} />

      <section className="pub-section pub-paper is-sheet">
        <div className="pub-inner pub-contact-grid">
          <div ref={letterRef} className="pub-letter-stage">
            <div className="pub-letter">
              <span className="pub-letter-icon">
                <Icon name="message" />
              </span>
              <h2>{t('contact.emailTitle')}</h2>
              <p>{t('contact.emailBody')}</p>
              <a className="pub-letter-mail" href="mailto:hello@kredibel.app">
                {t('contact.email')}
              </a>
              <div className="pub-letter-actions">
                <CopyEmailButton
                  email={t('contact.email')}
                  label={t('contact.copy')}
                  copied={t('contact.copied')}
                  failed={t('contact.copyFailed')}
                />
              </div>
            </div>
          </div>
          <div className="pub-contact-side">
            <div className="pub-contact-card">
              <span className="ico">
                <Icon name="eye" />
              </span>
              <div>
                <h2>{t('contact.showTitle')}</h2>
                <p>{t('contact.showBody')}</p>
              </div>
            </div>
            <div className="pub-contact-card">
              <span className="ico">
                <Icon name="info" />
              </span>
              <div>
                <h2>{t('contact.prototypeTitle')}</h2>
                <p>{t('contact.prototypeBody')}</p>
              </div>
            </div>
            <p className="pub-muted">{t('contact.note')}</p>
          </div>
        </div>
      </section>
    </PublicShell>
  )
}
