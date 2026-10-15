import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useProfitLoss } from '../../entities/profit-loss'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'

export function ProfitLossSources({ period }: { period: string }) {
  const { t } = useTranslation('profitLoss')
  const query = useProfitLoss(period)
  if (!query.data?.entries.length) return null
  const report = query.data
  const groups = [...new Set(report.entries.map((entry) => entry.subledger))].sort()
  return <section className="panel panel-pad stack gap-4">
    <h2 className="type-h2">{t('sources')}</h2><p>{t('sourceHelp')}</p>
    {groups.map((group) => <div key={group}>
      <h3 className="type-h3">{t(`subledgers.${group}`)}</h3>
      {report.entries.filter((entry) => entry.subledger === group).map((entry) => <Link className="pnl-source link" to={`/documents/${encodeURIComponent(entry.docId)}`} key={entry.entryId}>
        {t('source', { account: report.basis === 'CASH' ? entry.accountName : `${entry.accountCode} ${entry.accountName}`, date: formatDate(entry.date), row: entry.rowNumber, amount: formatMoney(entry.amount, { currency: report.currency, code: true }) })}
      </Link>)}
    </div>)}
  </section>
}
