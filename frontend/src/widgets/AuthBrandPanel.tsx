/**
 * The brand column of the onboarding mock (tools/design/mocks/screens.py `onboarding`): ledger
 * paper, tagline, the three promises and three ledger lines with what Kredibel does to each.
 * The lines are illustration only and say so in the small print.
 */

import { useTranslation } from 'react-i18next'
import { Icon, type IconName } from '../shared/ui/Icon'

const PROMISES: { icon: IconName; key: string }[] = [
  { icon: 'copy', key: 'brand.promiseCopies' },
  { icon: 'ai-reader', key: 'brand.promiseReadTwice' },
  { icon: 'reconcile', key: 'brand.promiseAnyOrder' },
]

export function AuthBrandPanel() {
  const { t } = useTranslation()

  return (
    <section className="onboard-brand" aria-label={t('app.name')}>
      <img className="logo" src="/brand/kredibel-logo-on-dark.svg" alt={t('app.name')} />
      <div className="stack gap-6">
        <p className="tagline">{t('brand.tagline')}</p>
        <ul className="promise">
          {PROMISES.map((promise) => (
            <li key={promise.key}>
              <Icon name={promise.icon} />
              <span>{t(promise.key)}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="ledger" aria-hidden="true">
        <div className="ledger-line">
          <span>{t('brand.ledger.outDate')}</span>
          <span className="desc">{t('brand.ledger.outText')}</span>
          <span className="amt">
            <span className="reading reading-agreed">{t('brand.ledger.outAmount')}</span>{' '}
            <span className="tick">
              <Icon name="ai-reader" size="sm" />
              {t('brand.ledger.outTick')}
            </span>
          </span>
        </div>
        <div className="ledger-line">
          <span>{t('brand.ledger.inDate')}</span>
          <span className="desc">{t('brand.ledger.inText')}</span>
          <span className="amt">
            {t('brand.ledger.inAmount')}{' '}
            <span className="tick">
              <Icon name="check" size="sm" />
              {t('brand.ledger.inTick')}
            </span>
          </span>
        </div>
        <div className="ledger-line">
          <span>{t('brand.ledger.copyDate')}</span>
          <span className="desc">{t('brand.ledger.copyText')}</span>
          <span className="amt">
            <span className="tick dup">
              <Icon name="copy" size="sm" />
              {t('brand.ledger.copyTick')}
            </span>
          </span>
        </div>
      </div>
      <p className="small-print">{t('brand.footnote')}</p>
    </section>
  )
}
