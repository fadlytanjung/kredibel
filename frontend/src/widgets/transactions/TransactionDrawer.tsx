/**
 * One transaction in the kit's drawer over the Transactions table (spec 024, AC-024-6): its
 * classes, subledger, reading and records, with the way to its statement, its month and each
 * record's document. Esc or the area beside the drawer closes it.
 */
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { Transaction } from '../../entities/transactions'
import { formatDate, formatMonth } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Icon } from '../../shared/ui'
import { categorizedBy } from './categorizedBy'
import { MATCH_CHIP, READING_MARK, RECORD_ICON } from './format'

export function TransactionDrawer({ tx, onClose }: { tx: Transaction; onClose: () => void }) {
  const { t } = useTranslation('transactions')
  const close = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    close.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const incoming = !tx.amount.amount.startsWith('-')
  const chip = MATCH_CHIP[tx.match.state] ?? MATCH_CHIP.UNMATCHED
  const facts: [string, string][] = [
    [t('drawer.date'), formatDate(tx.date)],
    [t('drawer.category'), `${tx.categoryLabel} (${categorizedBy(tx, t)})`],
    [t('drawer.ifrs'), t(`classes.${tx.cashflow.ifrs}`)],
    [t('drawer.usGaap'), t(`classes.${tx.cashflow.usGaap}`)],
    [t('drawer.pnl'), tx.pnlLine ?? '—'],
    [t('drawer.subledger'), tx.subledger ?? '—'],
  ]
  return (
    <div className="drawer-frame">
      <div className="drawer-behind" aria-hidden="true" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true" aria-labelledby="tx-h">
        <div className="drawer-head">
          <div className="stack gap-2 flex-1 min-w-0">
            <span className="muted small">{tx.counterpartyName ?? formatMonth(tx.month)}</span>
            <h1 id="tx-h">{tx.description.split('\n')[0]}</h1>
            <p className={incoming ? 'amt-in' : 'amt-out'}>
              <span className={`reading ${READING_MARK[tx.reading] ?? ''}`}>
                {incoming ? '+' : ''}
                {formatAmount(tx.amount.amount, { currency: tx.amount.currency })}
              </span>{' '}
              <small>{tx.amount.currency}</small>
            </p>
          </div>
          <button ref={close} type="button" className="icon-button" aria-label={t('drawer.close')} onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>
        <div className="drawer-body tx-body">
          <dl className="tx-facts">
            {facts.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
            <div>
              <dt>{t('drawer.reading')}</dt>
              <dd>{t(`reading.${tx.reading}`)}</dd>
            </div>
          </dl>
          <section className="stack gap-2" aria-labelledby="tx-matched-h">
            <h2 id="tx-matched-h" className="small muted">
              {t('drawer.matchedTo')}
            </h2>
            <span className={`match-chip ${chip.chip}`}>
              <Icon name={chip.icon} size="sm" />
              <span>{t(`match.${tx.match.state}`)}</span>
            </span>
            {tx.match.records.length === 0 ? (
              <p className="muted small">{t('drawer.nothing')}</p>
            ) : (
              <ul className="tx-records">
                {tx.match.records.map((r) => (
                  <li key={r.id}>
                    <Link className="link" to={`/documents/${r.docId}`}>
                      <Icon name={RECORD_ICON[r.kind] ?? 'file-text'} size="sm" />
                      {t(`records.${r.kind}`, { label: r.label })}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <div className="actions">
            <Link className="button button-secondary button-sm" to={`/documents/${tx.docId}`}>
              <Icon name="file-text" size="sm" />
              {t('drawer.statement')}
            </Link>
            <Link className="button button-quiet button-sm" to={`/months/${tx.month}`}>
              {t('drawer.month')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
