import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type ProfitLoss, useProfitLoss } from '../../entities/profit-loss'
import { formatMoney } from '../../shared/lib/formatMoney'
import { SegmentedControl } from '../../shared/ui'
import { ProfitLossFlow } from './ProfitLossFlow'

export function ProfitLossView({ report, detail = false }: { report: ProfitLoss; detail?: boolean }) {
  const { t } = useTranslation('profitLoss')
  const cash = report.basis === 'CASH'
  const hasEntries = (report.entries?.length ?? 0) > 0
  // The flow needs entries; the tab follows the report shown, not the first one loaded.
  const [chosen, setView] = useState<string | null>(null)
  const view = chosen === 'flow' && !hasEntries ? 'chart' : (chosen ?? (hasEntries ? 'flow' : 'chart'))
  const titleId = useId()
  // Floating point is used only for bar geometry; displayed amounts remain decimal strings.
  const max = Math.max(1, ...report.lines.map((line) => Math.abs(Number(line.amount ?? 0))))
  const amount = (value: string | null) =>
    value === null ? t('unavailableAmount') : formatMoney(value, { currency: report.currency, code: true })

  const viewOptions = [
    ...(hasEntries ? [{ key: 'flow', label: t('flow', { defaultValue: 'Flow' }) }] : []),
    { key: 'chart', label: t('bars', { defaultValue: 'Bars' }) },
    { key: 'table', label: t('table') },
  ]

  return (
    <section className="chart-panel panel-pad stack gap-4" aria-labelledby={titleId}>
      <div className="chart-head">
        <div>
          <h2 className="type-h2" id={titleId}>
            {t('title')}
          </h2>
          <p>{t(cash ? 'basisCash' : 'basis', { period: report.period })}</p>
        </div>
        {!detail && (
          <Link
            className="button button-secondary"
            to={`/profit-loss?period=${encodeURIComponent(report.period)}`}
          >
            {t('details')}
          </Link>
        )}
      </div>
      <p className="muted">{t(cash ? 'coverageCash' : 'coverage')}</p>
      {report.status === 'UNAVAILABLE' ? (
        <p role="status">{t(cash ? 'emptyCash' : 'empty')}</p>
      ) : (
        <>
          {report.status === 'PARTIAL' && <p role="status">{t('partial')}</p>}
          <SegmentedControl
            ariaLabel={t('view')}
            value={view}
            onChange={setView}
            options={viewOptions}
          />
          {view === 'flow' && <ProfitLossFlow report={report} />}
          {view === 'chart' && (
            <div className="pnl-bars" role="group" aria-label={t('title')}>
              {report.lines.map((line) => (
                <div className="pnl-row" key={line.id}>
                  <span>{t(`lines.${line.id}`)}</span>
                  <strong className="num">{amount(line.amount)}</strong>
                  <span className="pnl-track" aria-hidden="true">
                    <span
                      className="pnl-bar"
                      style={{ width: `${(Math.abs(Number(line.amount ?? 0)) / max) * 100}%` }} /* allow-raw-style: computed bar width */
                    />
                  </span>
                </div>
              ))}
            </div>
          )}
          {view === 'table' && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th scope="col">{t('line')}</th>
                    <th scope="col" className="num">
                      {t('amount')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {report.lines.map((line) => (
                    <tr key={line.id}>
                      <th scope="row">{t(`lines.${line.id}`)}</th>
                      <td className="num">{amount(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {(Object.keys(report.exclusions).length > 0 || report.gaps.length > 0) && (
        <ul>
          {Object.entries(report.exclusions).map(([reason, count]) => (
            <li key={reason}>{t(`exclusions.${reason}`, { count })}</li>
          ))}
          {report.gaps.map((gap) => (
            <li key={gap}>{t(`gaps.${gap}`)}</li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function ProfitLossPanel({ period, detail = false }: { period: string; detail?: boolean }) {
  const { t } = useTranslation('profitLoss')
  const query = useProfitLoss(period)
  if (query.isPending)
    return (
      <section className="panel panel-pad" role="status">
        {t('loading')}
      </section>
    )
  if (query.isError)
    return (
      <section className="panel panel-pad stack gap-3" role="alert">
        <p>{t('error')}</p>
        <button className="button button-secondary" onClick={() => void query.refetch()}>
          {t('retry')}
        </button>
      </section>
    )
  return <ProfitLossView report={query.data} detail={detail} />
}
