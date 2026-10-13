/**
 * Review (`/review`, `/review/:itemId`; spec 009, T009-05, T009-06; AC-009-2, AC-009-4, AC-009-7;
 * docs/11 §6.5): the open items in one table with chips by kind, the fix panel beside it on wide
 * screens and instead of it on phones. After a fix the next item opens.
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { type ReviewItem, useReviewItem, useReviewItems } from '../entities/review'
import { ItemPanel, KIND_ICON, monthName, useQueueKeys } from '../features/review'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../shared/ui'

// docs/11 §6.5: the order of the chips.
const KINDS = [
  'POSSIBLE_DUPLICATE',
  'PROPOSED_MATCH',
  'LEDGER_DIFFERENCE',
  'UNMATCHED_DOCUMENT',
  'UNMATCHED_BANK_LINE',
  'LOW_CONFIDENCE_VALUE',
  'CONFIRM_TYPE',
  'CONFIRM_LEDGER_MAPPING',
] as const
const TILE: Record<string, string> = { POSSIBLE_DUPLICATE: 'dup', PROPOSED_MATCH: 'match' }

export function ReviewPage() {
  const { t } = useTranslation('review')
  const navigate = useNavigate()
  const { itemId } = useParams()
  const { data, isLoading } = useReviewItems()
  const { data: opened } = useReviewItem(itemId)
  const [filter, setFilter] = useState('all')
  const [notice, setNotice] = useState<string>()

  const items = useMemo(() => data?.items ?? [], [data])
  const counts = data?.countsByKind ?? {}
  const visible = filter === 'all' ? items : items.filter((i) => i.kind === filter)
  const index = visible.findIndex((i) => i.itemId === itemId)
  const current = opened?.status === 'OPEN' ? opened : visible[index]

  const open = (item: ReviewItem | undefined) => navigate(item ? `/review/${item.itemId}` : '/review')
  const step = (by: number) => {
    if (visible.length === 0) return
    open(visible[(Math.max(index, by > 0 ? -1 : 0) + by + visible.length) % visible.length])
  }
  useQueueKeys(useMemo(() => ({ next: () => step(1), previous: () => step(-1) }), [visible, index])) // eslint-disable-line react-hooks/exhaustive-deps

  const resolved = (item: ReviewItem) => {
    const rest = visible.filter((i) => i.itemId !== item.itemId)
    const next = rest[Math.min(Math.max(index, 0), rest.length - 1)]
    const updating = item.month ? t('panel.updating', { month: monthName(item.month) }) : ''
    const left = next ? t('panel.next', { count: rest.length }) : t('panel.allDone')
    setNotice([updating, left].filter(Boolean).join(' '))
    open(next)
  }

  const filters: DataTableFilter<ReviewItem>[] = [
    { key: 'all', label: t('all'), count: items.length },
    ...KINDS.filter((k) => counts[k]).map((k) => ({
      key: k,
      label: t(`kinds.${k}`),
      count: counts[k],
      predicate: (i: ReviewItem) => i.kind === k,
    })),
  ]
  const columns: DataTableColumn<ReviewItem>[] = [
    {
      key: 'item',
      header: t('colItem'),
      wideOnMobile: true,
      render: (i) => (
        <div className="qitem">
          <span className={`kind ${TILE[i.kind] ?? 'doc'}`}>
            <Icon name={KIND_ICON[i.kind] ?? 'inbox'} size="sm" />
          </span>
          <span className="t">{i.title}</span>
          <span className="s">{t(`kinds.${i.kind}`)}</span>
        </div>
      ),
    },
    {
      key: 'month',
      header: t('colMonth'),
      hideOnMobile: true,
      sortable: true,
      sortValue: (i) => i.month ?? '',
      render: (i) => (i.month ? monthName(i.month) : t('noMonth')),
    },
  ]

  const queue = (
    <section className={`stack gap-3 ${current ? 'hide-compact' : ''}`} aria-label={t('open', { count: items.length })}>
      {notice && (
        <p className="flow-callout" role="status">
          <Icon name="check-circle" size="sm" />
          <span>{notice}</span>
        </p>
      )}
      <DataTable
        data={items}
        columns={columns}
        getRowKey={(i) => i.itemId}
        filters={filters}
        activeFilter={filter}
        onFilterChange={setFilter}
        filterGroupAriaLabel={t('filterLabel')}
        searchable
        searchPlaceholder={t('search')}
        searchPredicate={(i, q) => [i.title, t(`kinds.${i.kind}`), i.month ? monthName(i.month) : ''].some((s) => s.toLowerCase().includes(q))}
        isLoading={isLoading}
        loadingMessage={<p className="muted">{t('loading')}</p>}
        emptyMessage={<p className="muted">{t('empty')}</p>}
        onRowClick={open}
        selectedRowKey={itemId}
      />
    </section>
  )

  return (
    <div className="page review stack gap-6">
      <header className="stack gap-2">
        <h1 className="type-title">{t('title')}</h1>
        <p className="muted">{t('subtitle')}</p>
      </header>
      {current ? (
        <div className="review-layout">
          {queue}
          <ItemPanel
            key={current.itemId}
            item={current}
            position={{ index: Math.max(index, 0), total: Math.max(visible.length, 1) }}
            onResolved={resolved}
            onSkip={() => step(1)}
            onClose={() => open(undefined)}
          />
        </div>
      ) : (
        queue
      )}
      {itemId && opened && opened.status !== 'OPEN' && !current && <p className="muted">{t('panel.missing')}</p>}
    </div>
  )
}
