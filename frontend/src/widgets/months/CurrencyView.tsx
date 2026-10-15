/**
 * Currency (spec 007, T007-10c, AC-007-19; ADR-025): a document printed in another currency waits
 * for agreement before its amounts count as the workspace's, without conversion. Agreeing keeps
 * the numbers and the printed currency and is audited; no exchange rates anywhere.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useCreateDecision } from '../../entities/decision'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Button, Icon } from '../../shared/ui'
import { type Row, rowTitle, rowWho } from '../month'

export function CurrencyView({ rows, currency, isLoading }: { rows: Row[]; currency: string; isLoading: boolean }) {
  const { t } = useTranslation(['months', 'common'])
  const create = useCreateDecision()
  const [status, setStatus] = useState('')
  const pending = rows.filter((r) => r.payment === 'CURRENCY_TO_CONFIRM')
  return (
    <section className="stack gap-4" aria-labelledby="currency-check-h">
      <h2 className="type-h2" id="currency-check-h">
        {t('months:all.currency.title')}
      </h2>
      <p className="muted">{t('months:all.currency.intro', { currency })}</p>
      {status && (
        <p className="muted" role="status">
          {status}
        </p>
      )}
      {isLoading ? (
        <p className="muted">{t('months:all.loading')}</p>
      ) : pending.length === 0 ? (
        <p className="muted">{t('months:all.currency.none', { currency })}</p>
      ) : (
        pending.map((r) => {
          const printed = r.printedCurrency ?? r.total?.currency ?? ''
          const amount = formatAmount(r.total?.amount ?? '0', { currency: printed || currency })
          return (
            <article key={r.id} className="card stack gap-3" aria-label={rowTitle(t, r)}>
              <span className="badge badge-medium self-start">
                <Icon name="circle-alert" size="sm" />
                {t('months:all.currency.badge')}
              </span>
              <p>
                <strong>{rowTitle(t, r)}</strong>
                <span className="muted"> · {rowWho(t, r)}</span>
              </p>
              <p>{t('months:all.currency.question', { printed, amount, currency })}</p>
              <p className="muted">{t('months:all.currency.keep')}</p>
              <div className="row gap-3 flex-wrap">
                <Button
                  disabled={create.isPending}
                  onClick={() =>
                    create.mutate(
                      { kind: 'CURRENCY_AGREEMENT', docId: r.docId },
                      { onSuccess: () => setStatus(t('months:all.currency.agreed', { title: rowTitle(t, r), currency })) },
                    )
                  }
                >
                  {t('months:all.currency.use', { currency })}
                </Button>
                <Link className="button button-secondary" to="/documents?upload=1">
                  {t('months:all.currency.replace')}
                </Link>
              </div>
            </article>
          )
        })
      )}
    </section>
  )
}
