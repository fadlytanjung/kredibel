/**
 * design/mocks/transactions.html (spec 024, AC-024-6): every bank line of a month, one row each,
 * with its category, its cash-flow class under IFRS and US GAAP, its subledger, how sure the
 * category is, how its values were read and what it is matched to. A row opens in the drawer.
 */
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useMonths } from '../entities/month'
import { useTransactions, type Transaction } from '../entities/transactions'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { formatAmount } from '../shared/lib/formatMoney'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../shared/ui'
import { categorizedBy, MATCH_CHIP, READING_MARK, TransactionDrawer } from '../widgets/transactions'

const STATES = ['AUTO', 'MANUAL', 'PROPOSED', 'UNMATCHED'] as const

export function TransactionsContent({ basePath = '/transactions' }: { basePath?: string }) {
  const { t } = useTranslation(['transactions', 'common'])
  const navigate = useNavigate()
  const { txId } = useParams<{ txId?: string }>()
  const [params, setParams] = useSearchParams()
  const { data: monthList } = useMonths()
  const months = (monthList?.items ?? []).map((m) => m.month).sort().reverse()
  const withLines = (monthList?.items ?? []).filter((m) => (m.statements ?? []).length > 0).map((m) => m.month).sort()
  const month = params.get('month') ?? withLines[withLines.length - 1] ?? months[0]
  const { data, isLoading } = useTransactions(month)
  const items = data?.items ?? []
  const open = items.find((tx) => tx.txId === txId)
  const query = month ? `?month=${month}` : ''

  const filters: DataTableFilter<Transaction>[] = [
    { key: 'all', label: t('filters.all'), predicate: () => true, count: items.length },
    ...STATES.map((state) => ({
      key: state,
      label: t(`filters.${state}`),
      predicate: (tx: Transaction) => tx.match.state === state,
      count: items.filter((tx) => tx.match.state === state).length,
    })),
  ]
  const columns: DataTableColumn<Transaction>[] = [
    { key: 'date', header: t('columns.date'), sortable: true, sortValue: (tx) => tx.date, render: (tx) => formatDate(tx.date) },
    {
      key: 'description',
      header: t('columns.description'),
      wideOnMobile: true,
      render: (tx) => (
        <div className="stack gap-1">
          <strong>{tx.counterpartyName || tx.description.split('\n')[0]}</strong>
          {tx.counterpartyName && <span className="reason">{tx.description.split('\n')[0]}</span>}
        </div>
      ),
    },
    {
      key: 'amount',
      header: t('columns.amount'),
      align: 'right',
      sortable: true,
      sortValue: (tx) => Number(tx.amount.amount),
      render: (tx) => {
        const incoming = !tx.amount.amount.startsWith('-')
        return (
          <span className={incoming ? 'amt-in' : 'amt-out'}>
            <span className={`reading ${READING_MARK[tx.reading] ?? ''}`}>
              {incoming ? '+' : ''}
              {formatAmount(tx.amount.amount, { currency: tx.amount.currency })}
            </span>
          </span>
        )
      },
    },
    {
      key: 'category',
      header: t('columns.category'),
      render: (tx) => (
        <div className="stack gap-1">
          <span>{tx.categoryLabel}</span>
          <span className="reason">{categorizedBy(tx, t)}</span>
        </div>
      ),
    },
    { key: 'ifrs', header: t('columns.ifrs'), hideOnMobile: true, className: 'small', render: (tx) => t(`classes.${tx.cashflow.ifrs}`) },
    { key: 'usGaap', header: t('columns.usGaap'), hideOnMobile: true, className: 'small', render: (tx) => t(`classes.${tx.cashflow.usGaap}`) },
    {
      key: 'subledger',
      header: t('columns.subledger'),
      hideOnMobile: true,
      className: 'small',
      render: (tx) => (
        <div className="stack gap-1">
          <span>{tx.subledger ?? '—'}</span>
          {tx.pnlLine && <span className="reason">{tx.pnlLine}</span>}
        </div>
      ),
    },
    { key: 'reading', header: t('columns.reading'), hideOnMobile: true, className: 'small', render: (tx) => t(`reading.${tx.reading}`) },
    {
      key: 'match',
      header: t('columns.match'),
      render: (tx) => {
        const chip = MATCH_CHIP[tx.match.state] ?? MATCH_CHIP.UNMATCHED
        return (
          <div className="stack gap-1">
            <span className={`match-chip ${chip.chip}`}>
              <Icon name={chip.icon} size="sm" />
              <span>{t(`match.${tx.match.state}`)}</span>
            </span>
            {tx.match.records.length > 0 && <span className="reason">{tx.match.records.map((r) => t(`records.${r.kind}`, { label: r.label })).join(', ')}</span>}
          </div>
        )
      },
    },
  ]

  const monthPicker = (
    <select
      className="select select-sm"
      aria-label={t('month')}
      value={month ?? ''}
      onChange={(e) => {
        setParams({ month: e.target.value })
        if (txId) navigate(`${basePath}?month=${e.target.value}`)
      }}
    >
      {months.map((m) => (
        <option key={m} value={m}>
          {formatMonth(m)}
        </option>
      ))}
    </select>
  )

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t('title')}</h1>
        <p>{t('subtitle')}</p>
      </div>
      <DataTable
        key={month}
        data={items}
        columns={columns}
        getRowKey={(tx) => tx.txId}
        filters={filters}
        filterGroupAriaLabel={t('filters.label')}
        searchPlaceholder={t('search')}
        searchPredicate={(tx, q) => [tx.description, tx.counterpartyName ?? '', tx.categoryLabel].some((text) => text.toLowerCase().includes(q))}
        headerActions={monthPicker}
        isLoading={isLoading}
        emptyMessage={<p className="muted">{t('empty')}</p>}
        onRowClick={(tx) => navigate(`${basePath}/${encodeURIComponent(tx.txId)}${query}`)}
        selectedRowKey={txId}
        tableClassName="tx-table"
      />
      {open && <TransactionDrawer tx={open} onClose={() => navigate(`${basePath}${query}`)} />}
    </div>
  )
}

export function TransactionsPage() {
  return <TransactionsContent />
}
