/**
 * One client or supplier (spec 014, AC-014-2): its totals by month, the accounts seen with first
 * and last use, its bank lines and its invoices and receipts.
 */

import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { useCounterparty } from '../entities/counterparty'
import { useWorkspace } from '../entities/workspace'
import { apiClient } from '../shared/api/client'
import type { components } from '../shared/api/schema'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { formatMoney } from '../shared/lib/formatMoney'
import { DataTable, type DataTableColumn, Icon } from '../shared/ui'

type BankLine = components['schemas']['BankLine']
type Invoice = components['schemas']['Invoice']
type Receipt = components['schemas']['Receipt']
type Counterparty = components['schemas']['Counterparty']
type MonthTotals = NonNullable<Counterparty['totalsByMonth']>[string]
type AccountSeen = NonNullable<Counterparty['accountsSeen']>[number]
interface DocumentRow {
  id: string
  docId: string
  label: string
  date: string | null
  total: string | null
  payment: string | null
}

function useLinesOf(counterpartyId: string | undefined) {
  return useQuery({
    queryKey: ['bank-lines', { counterpartyId }],
    queryFn: () => apiClient<{ items: BankLine[] }>(`/api/bank-lines?counterpartyId=${counterpartyId}`),
    enabled: Boolean(counterpartyId),
  })
}

function useRecordsOf(counterpartyId: string | undefined) {
  return useQuery({
    queryKey: ['records', { counterpartyId }],
    queryFn: async () => {
      const [invoices, receipts] = await Promise.all([
        apiClient<{ items: Invoice[] }>(`/api/invoices?counterpartyId=${counterpartyId}`),
        apiClient<{ items: Receipt[] }>(`/api/receipts?counterpartyId=${counterpartyId}`),
      ])
      return { invoices: invoices.items, receipts: receipts.items }
    },
    enabled: Boolean(counterpartyId),
  })
}

export function CounterpartyPage() {
  const { t } = useTranslation(['counterparties', 'months'])
  const { id } = useParams<{ id: string }>()
  const { data: workspace } = useWorkspace()
  const { data: party, isLoading, isError } = useCounterparty(id)
  const { data: lines } = useLinesOf(id)
  const { data: records } = useRecordsOf(id)
  const currency = workspace?.currency ?? 'IDR'

  if (isLoading) return <p className="muted panel-pad">{t('detail.loading')}</p>
  if (isError || !party) return <p className="muted panel-pad">{t('detail.notFound')}</p>

  const months = Object.entries(party.totalsByMonth ?? {}).sort(([a], [b]) => a.localeCompare(b))
  const accounts = party.accountsSeen ?? []
  const documents: DocumentRow[] = [
    ...(records?.invoices ?? []).map((inv) => ({
      id: inv.invoiceId,
      docId: inv.docId,
      label: inv.number ?? inv.invoiceId,
      date: inv.issueDate ?? null,
      total: inv.total?.amount ?? null,
      payment: inv.evidence?.payment ?? null,
    })),
    ...(records?.receipts ?? []).map((rc) => ({
      id: rc.receiptId,
      docId: rc.docId,
      label: rc.merchantName ?? rc.receiptId,
      date: rc.date ?? null,
      total: rc.total?.amount ?? null,
      payment: rc.evidence?.payment ?? null,
    })),
  ]
  const money = (amount: string | null | undefined) => (amount ? formatMoney(amount, { currency }) : '—')
  // On phones each row is a two-column grid: the first column spans it, the next two share a line.
  const monthColumns: DataTableColumn<[string, MonthTotals]>[] = [
    { key: 'month', header: t('detail.colMonth'), wideOnMobile: true, render: ([month]) => formatMonth(month) },
    { key: 'in', header: t('detail.colIn'), align: 'right', render: ([, totals]) => <span className="amt-in">{money(totals.in?.amount)}</span> },
    { key: 'out', header: t('detail.colOut'), align: 'right', render: ([, totals]) => <span className="amt-out">{money(totals.out?.amount)}</span> },
    { key: 'count', header: t('detail.colCount'), align: 'right', hideOnMobile: true, render: ([, totals]) => totals.count ?? 0 },
  ]
  const accountColumns: DataTableColumn<AccountSeen>[] = [
    { key: 'account', header: t('detail.colAccount'), wideOnMobile: true, render: (a) => a.accountMasked },
    { key: 'first', header: t('detail.colFirst'), render: (a) => (a.firstSeen ? formatDate(a.firstSeen) : '—') },
    { key: 'last', header: t('detail.colLast'), align: 'right', render: (a) => (a.lastSeen ? formatDate(a.lastSeen) : '—') },
  ]
  const lineColumns: DataTableColumn<BankLine>[] = [
    { key: 'description', header: t('detail.colDescription'), wideOnMobile: true, render: (ln) => ln.description },
    { key: 'date', header: t('detail.colDate'), render: (ln) => formatDate(ln.date) },
    {
      key: 'amount',
      header: t('detail.colAmountLine'),
      align: 'right',
      render: (ln) => <span className={Number(ln.amount.amount) >= 0 ? 'amt-in' : 'amt-out'}>{money(ln.amount.amount)}</span>,
    },
  ]
  const documentColumns: DataTableColumn<DocumentRow>[] = [
    { key: 'document', header: t('detail.colDocument'), wideOnMobile: true, render: (d) => <Link className="link" to={`/documents/${d.docId}`}>{d.label}</Link> },
    { key: 'date', header: t('detail.colDate'), render: (d) => (d.date ? formatDate(d.date) : '—') },
    { key: 'total', header: t('detail.colTotal'), align: 'right', render: (d) => money(d.total) },
    { key: 'payment', header: t('detail.colPayment'), wideOnMobile: true, render: (d) => (d.payment ? t(`months:monthDetail.payment.${d.payment}`, { defaultValue: d.payment }) : '—') },
  ]

  return (
    <div className="page stack gap-6">
      <header className="page-head stack gap-2">
        <Link className="link small" to="/counterparties">
          <Icon name="chevron-left" size="sm" />
          {t('detail.back')}
        </Link>
        <h1 className="type-title">{party.name}</h1>
        <p className="muted">
          {party.roles.map((r) => t(`roles.${r}`)).join(', ')}
          {party.aliases && party.aliases.length > 0 ? ` · ${t('detail.aliases', { aliases: party.aliases.join(', ') })}` : ''}
        </p>
      </header>

      <section className="ledger" aria-label={t('detail.moneyIn')}>
        <dl className="ledger-figures">
          <div className="figure">
            <dt>{t('detail.moneyIn')}</dt>
            <dd className="v">{formatMoney(party.totalIn?.amount ?? '0', { currency })}</dd>
          </div>
          <div className="figure">
            <dt>{t('detail.moneyOut')}</dt>
            <dd className="v">{formatMoney(party.totalOut?.amount ?? '0', { currency })}</dd>
          </div>
          <div className="figure">
            <dt>{t('detail.openInvoices')}</dt>
            <dd className="v">{party.openInvoices ?? 0}</dd>
          </div>
          <div className="figure">
            <dt>{t('detail.firstSeen')}</dt>
            <dd className="v">{party.firstDate ? formatDate(party.firstDate) : '—'}</dd>
          </div>
          <div className="figure">
            <dt>{t('detail.lastSeen')}</dt>
            <dd className="v">{party.lastDate ? formatDate(party.lastDate) : '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="panel" aria-labelledby="cp-months-h">
        <div className="panel-head"><h2 id="cp-months-h">{t('detail.months')}</h2></div>
        <DataTable
          data={months}
          columns={monthColumns}
          getRowKey={([month]) => month}
          paginated={false}
          searchable={false}
          emptyMessage={<p className="muted">{t('detail.noLines')}</p>}
        />
      </section>

      <section className="panel" aria-labelledby="cp-accounts-h">
        <div className="panel-head"><h2 id="cp-accounts-h">{t('detail.accounts')}</h2></div>
        <DataTable
          data={accounts}
          columns={accountColumns}
          getRowKey={(a) => a.accountMasked ?? ''}
          paginated={false}
          searchable={false}
          emptyMessage={<p className="muted">{t('detail.noAccounts')}</p>}
        />
      </section>

      <section className="panel" aria-labelledby="cp-lines-h">
        <div className="panel-head"><h2 id="cp-lines-h">{t('detail.lines')}</h2></div>
        <DataTable
          data={lines?.items ?? []}
          columns={lineColumns}
          getRowKey={(ln) => ln.txId}
          paginated={false}
          searchable={false}
          emptyMessage={<p className="muted">{t('detail.noLines')}</p>}
        />
      </section>

      <section className="panel" aria-labelledby="cp-docs-h">
        <div className="panel-head"><h2 id="cp-docs-h">{t('detail.documents')}</h2></div>
        <DataTable
          data={documents}
          columns={documentColumns}
          getRowKey={(d) => d.id}
          paginated={false}
          searchable={false}
          emptyMessage={<p className="muted">{t('detail.noDocuments')}</p>}
        />
      </section>
    </div>
  )
}
