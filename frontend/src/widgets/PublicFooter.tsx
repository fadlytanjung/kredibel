import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useInViewAttr } from '../shared/lib/useInViewAttr'
import { FOOTER_COMPANY, FOOTER_LEGAL, FOOTER_PRODUCT } from './publicNav'

/**
 * The public site footer (spec 018, AC-018-6): the tagline set wide as a closing statement (it opens
 * from a condensed width once, on arrival), the brand blurb, the product/company/legal columns and the
 * small print, on ink ledger paper.
 */
export function PublicFooter() {
  const { t } = useTranslation('public')
  const ref = useRef<HTMLElement>(null)
  const inView = useInViewAttr(ref)

  return (
    <footer ref={ref} className="pub-ink pub-footer" {...inView}>
      <div className="pub-inner">
        <p className="pub-footer-tagline">{t('footer.tagline')}</p>
        <div className="pub-footer-grid">
          <div className="pub-footer-blurb">
            <img src="/brand/kredibel-logo-on-dark.svg" alt={t('nav.home')} />
            <p>{t('footer.blurb')}</p>
          </div>
          <div>
            <h3>{t('footer.product')}</h3>
            <ul>
              {FOOTER_PRODUCT.map((item) => (
                <li key={item.key}>
                  <Link to={item.to}>{t(`nav.${item.key}`)}</Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>{t('footer.company')}</h3>
            <ul>
              {FOOTER_COMPANY.map((item) => (
                <li key={item.key}>
                  <Link to={item.to}>{t(`footer.${item.key}`)}</Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3>{t('footer.legal')}</h3>
            <ul>
              {FOOTER_LEGAL.map((item) => (
                <li key={item.key}>
                  <Link to={item.to}>{t(`footer.${item.key}`)}</Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div className="pub-footer-bottom">
          <span>
            {t('footer.copyright')} {t('footer.promise')}
          </span>
          <span>{t('footer.synthetic')}</span>
        </div>
      </div>
    </footer>
  )
}
