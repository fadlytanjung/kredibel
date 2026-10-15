/**
 * Clients and suppliers (spec 014, AC-014-2; docs/11 §6.7): role chips with counts, the table of
 * names with the period's amount, the share of money in or out, transfers and accounts seen. A
 * supplier paid to a new account (X08) or never paid (R02) is flagged; a row opens its detail.
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useCounterparties, type Counterparty, type CounterpartyRole } from '../entities/counterparty'
import { useWorkspace } from '../entities/workspace'
import { formatMonth } from '../shared/lib/formatDate'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon, type IconName } from '../shared/ui'

const ROLE_ORDER: CounterpartyRole[] = ['CLIENT', 'SUPPLIER', 'LENDER', 'OWNER', 'OWN_ACCOUNT', 'GOVERNMENT', 'RELATED_PARTY', 'OTHER']
const KIND_ICON: Record<string, IconName> = { BUSINESS: 'building', BANK: 'bank', PERSON: 'user', GOVERNMENT: 'building', UNKNOWN: 'users' }

function millions(amount: string): string {
  return (Number(amount) / 1_000_000).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function transfersOf(party: Counterparty): number {
  return Object.values(party.totalsByMonth ?? {}).reduce((n, t) => n + (t.count ?? 0), 0)
}

function isMoneyIn(party: Counterparty): boolean {
  return Number(party.totalIn?.amount ?? 0) >= Number(party.totalOut?.amount ?? 0)
}

/** "Jan to Jun" from the parties' first and last dates. */
function rangeOf(parties: Counterparty[]): string {
  const months = parties.flatMap((p) => Object.keys(p.totalsByMonth ?? {})).sort()
  if (months.length === 0) return ''
  const first = formatMonth(months[0], 'short')
  const last = formatMonth(months[months.length - 1], 'short')
  return first === last ? first : `${first} to ${last}`
}

export function CounterpartiesPage() {
  const { t } = useTranslation('counterparties')
  const navigate = useNavigate()
  const { data: workspace } = useWorkspace()
  const { data, isLoading } = useCounterparties()
  const [filter, setFilter] = useState('all')
  const parties = useMemo(() => data?.items ?? [], [data])
  const currency = workspace?.currency ?? 'IDR'
  const range = rangeOf(parties)
  const totalIn = parties.reduce((n, p) => n + Number(p.totalIn?.amount ?? 0), 0)
  const totalOut = parties.reduce((n, p) => n + Number(p.totalOut?.amount ?? 0), 0)

  const counts = ROLE_ORDER.reduce<Record<string, number>>((acc, role) => {
    acc[role] = parties.filter((p) => p.roles.includes(role)).length
    return acc
  }, {})
  const filters: DataTableFilter<Counterparty>[] = [
    { key: 'all', label: t('all'), count: parties.length },
    ...ROLE_ORDER.filter((role) => counts[role]).map((role) => ({
      key: role,
      label: t(`rolesPlural.${role}`),
      count: counts[role],
      predicate: (p: Counterparty) => p.roles.includes(role),
    })),
  ]

  const columns: DataTableColumn<Counterparty>[] = [
    {
      key: 'name',
      header: t('colName'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (p) => p.name,
      render: (p) => (
        <span className="doc-cell">
          <span className="thumb">
            <Icon name={KIND_ICON[p.kind ?? 'UNKNOWN'] ?? 'users'} size="sm" />
          </span>
          <span>
            <strong>{p.name}</strong>
            <span className="sub">{p.roles.map((r) => t(`roles.${r}`)).join(', ')}</span>
          </span>
        </span>
      ),
    },
    {
      key: 'amount',
      header: t('colAmount', { currency, range }),
      align: 'right',
      sortable: true,
      sortValue: (p) => Number(isMoneyIn(p) ? p.totalIn?.amount : p.totalOut?.amount) || 0,
      render: (p) => {
        const inward = isMoneyIn(p)
        const value = inward ? p.totalIn?.amount : p.totalOut?.amount
        if (!value || Number(value) === 0) return <span className="muted">0.0</span>
        return <span className={inward ? 'amt-in' : 'amt-out'}>{inward ? '+' : '−'}{millions(value)}</span>
      },
    },
    {
      key: 'share',
      header: t('colShare'),
      hideOnMobile: true,
      render: (p) => {
        const inward = isMoneyIn(p)
        const value = Number((inward ? p.totalIn?.amount : p.totalOut?.amount) ?? 0)
        const total = inward ? totalIn : totalOut
        const share = total > 0 ? (value / total) * 100 : 0
        return (
          <span className="share">
            {/* allow-raw-style: the share bar's width is computed from the party's share */}
            <span className="meter-bar"><i style={{ width: `${Math.min(100, share * 3).toFixed(0)}%` }} /></span>{/* allow-raw-style: computed geometry */}
            <span>{share.toFixed(1)}%</span>
          </span>
        )
      },
    },
    {
      key: 'transfers',
      header: t('colTransfers'),
      align: 'right',
      hideOnMobile: true,
      sortable: true,
      sortValue: (p) => transfersOf(p),
      render: (p) => transfersOf(p),
    },
    {
      key: 'accounts',
      header: t('colAccounts'),
      render: (p) => {
        const accounts = p.accountsSeen ?? []
        const newest = accounts.length >= 2 ? [...accounts].sort((a, b) => (a.firstSeen ?? '').localeCompare(b.firstSeen ?? ''))[accounts.length - 1] : null
        const unpaid = (p.openInvoices ?? 0) > 0 && transfersOf(p) === 0 ? p.openInvoices ?? 0 : 0
        return (
          <>
            {t('accounts', { count: accounts.length })}{' '}
            {newest && (
              <Link className="badge badge-high" to="/risk" onClick={(e) => e.stopPropagation()}>
                <Icon name="triangle-alert" size="sm" />
                {t('newAccount', { month: newest.firstSeen ? formatMonth(newest.firstSeen.slice(0, 7), 'long') : '' })}
              </Link>
            )}
            {!newest && unpaid > 0 && (
              <Link className="badge badge-medium" to="/risk" onClick={(e) => e.stopPropagation()}>
                <Icon name="circle-alert" size="sm" />
                {t('unpaid', { count: unpaid })}
              </Link>
            )}
          </>
        )
      },
    },
  ]

  return (
    <div className="page stack gap-6">
      <header className="page-head stack gap-2">
        <h1 className="type-title">{t('title')}</h1>
        <p className="muted">{t('subtitle')}</p>
      </header>
      <div className="stack gap-3">
        <DataTable
          data={parties}
          columns={columns}
          getRowKey={(p) => p.counterpartyId}
          filters={filters}
          activeFilter={filter}
          onFilterChange={setFilter}
          filterGroupAriaLabel={t('filterLabel')}
          searchable
          searchPlaceholder={t('search')}
          searchPredicate={(p, q) => [p.name, ...(p.aliases ?? [])].some((s) => s.toLowerCase().includes(q))}
          isLoading={isLoading}
          loadingMessage={<p className="muted">{t('loading')}</p>}
          emptyMessage={<p className="muted">{t('empty')}</p>}
          paginated={false}
          onRowClick={(p) => navigate(`/counterparties/${p.counterpartyId}`)}
          rowClassName={(p) => ((p.accountsSeen?.length ?? 0) >= 2 ? 'is-flagged' : undefined)}
        />
        <p className="muted small">{t('footnote')}</p>
      </div>
    </div>
  )
}
