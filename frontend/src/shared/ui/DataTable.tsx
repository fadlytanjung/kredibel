/**
 * Reusable DataTable component (Design system §5, responsive table §5a).
 *
 * Features:
 * - Responsive table (.table-panel .rt-wrap, .data-table .rt)
 * - Integrated search with live filtering, icon, and clear button
 * - Filter chips with active state, ARIA pressed, and item counts
 * - Pagination with configurable page size, range text, and prev/next controls
 * - Sortable columns support
 * - Row selection and click handler with keyboard accessibility (Enter/Space)
 * - Custom empty state and loading state
 * - Custom header actions slot and footer slot
 */

import { type ReactNode, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from './Button'
import { Icon } from './Icon'

export interface DataTableColumn<T> {
  key: string
  header: ReactNode
  render: (item: T, index: number) => ReactNode
  align?: 'left' | 'right'
  className?: string
  hideOnMobile?: boolean
  wideOnMobile?: boolean
  sortable?: boolean
  sortValue?: (item: T) => string | number | Date | null | undefined
}

export interface DataTableFilter<T> {
  key: string
  label: string
  predicate?: (item: T) => boolean
  count?: number
}

export interface DataTableProps<T> {
  data: T[]
  columns: DataTableColumn<T>[]
  getRowKey: (item: T, index: number) => string
  searchable?: boolean
  searchPlaceholder?: string
  searchPredicate?: (item: T, query: string) => boolean
  filters?: DataTableFilter<T>[]
  activeFilter?: string
  onFilterChange?: (filterKey: string) => void
  filterGroupAriaLabel?: string
  paginated?: boolean
  pageSize?: number
  rangeLabel?: (from: number, to: number, total: number) => ReactNode
  isLoading?: boolean
  loadingMessage?: ReactNode
  emptyMessage?: ReactNode
  headerActions?: ReactNode
  footer?: ReactNode
  onRowClick?: (item: T) => void
  selectedRowKey?: string
  rowClassName?: (item: T) => string | undefined
  tableClassName?: string
  ariaLabel?: string
}

export function DataTable<T>({
  data,
  columns,
  getRowKey,
  searchable = true,
  searchPlaceholder,
  searchPredicate,
  filters,
  activeFilter,
  onFilterChange,
  filterGroupAriaLabel,
  paginated = true,
  pageSize = 25,
  rangeLabel,
  isLoading = false,
  loadingMessage,
  emptyMessage,
  headerActions,
  footer,
  onRowClick,
  selectedRowKey,
  rowClassName,
  tableClassName = '',
  ariaLabel,
}: DataTableProps<T>) {
  const { t } = useTranslation(['common', 'documents'])
  const [internalFilter, setInternalFilter] = useState<string>(filters?.[0]?.key ?? 'all')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const currentFilterKey = activeFilter ?? internalFilter

  const handleFilterSelect = (key: string) => {
    if (onFilterChange) {
      onFilterChange(key)
    } else {
      setInternalFilter(key)
    }
    setCurrentPage(0)
  }

  // 1. Filter by active filter chip
  const filteredByChip = useMemo(() => {
    if (!filters || filters.length === 0) return data
    const activeChip = filters.find((f) => f.key === currentFilterKey)
    if (!activeChip?.predicate) return data
    return data.filter(activeChip.predicate)
  }, [data, filters, currentFilterKey])

  // 2. Filter by search query
  const filteredBySearch = useMemo(() => {
    const q = searchQuery.trim().toLowerCase()
    if (!q) return filteredByChip

    if (searchPredicate) {
      return filteredByChip.filter((item) => searchPredicate(item, q))
    }

    // Default search predicate: check string and number values of the item
    return filteredByChip.filter((item) => {
      const itemRecord = item as Record<string, unknown>
      for (const val of Object.values(itemRecord)) {
        if (typeof val === 'string' && val.toLowerCase().includes(q)) return true
        if (typeof val === 'number' && String(val).includes(q)) return true
        if (typeof val === 'object' && val !== null) {
          try {
            if (JSON.stringify(val).toLowerCase().includes(q)) return true
          } catch {
            // ignore cyclic or non-serializable objects
          }
        }
      }
      return false
    })
  }, [filteredByChip, searchQuery, searchPredicate])

  // 3. Sort if a column is actively sorted
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredBySearch
    const col = columns.find((c) => c.key === sortKey)
    if (!col?.sortValue) return filteredBySearch

    return [...filteredBySearch].sort((a, b) => {
      const valA = col.sortValue!(a)
      const valB = col.sortValue!(b)
      if (valA === valB) return 0
      if (valA === null || valA === undefined) return 1
      if (valB === null || valB === undefined) return -1
      const res = valA < valB ? -1 : 1
      return sortDir === 'asc' ? res : -res
    })
  }, [filteredBySearch, sortKey, sortDir, columns])

  // 4. Paginate
  const totalCount = sortedData.length
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const paginatedData = useMemo(() => {
    if (!paginated) return sortedData
    const start = currentPage * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, paginated, currentPage, pageSize])

  const handleSortToggle = (col: DataTableColumn<T>) => {
    if (!col.sortable) return
    if (sortKey === col.key) {
      if (sortDir === 'asc') {
        setSortDir('desc')
      } else {
        setSortKey(null)
      }
    } else {
      setSortKey(col.key)
      setSortDir('asc')
    }
  }

  const rangeStart = totalCount === 0 ? 0 : currentPage * pageSize + 1
  const rangeEnd = Math.min((currentPage + 1) * pageSize, totalCount)

  const hasToolbar = Boolean(
    (filters && filters.length > 0) || searchable || headerActions,
  )

  return (
    <div className="stack gap-3">
      {hasToolbar && (
        <div className="table-toolbar">
          {filters && filters.length > 0 && (
            <div
              className="chips"
              role="group"
              aria-label={filterGroupAriaLabel ?? t('common:table.filter', { defaultValue: 'Filter items' })}
            >
              {filters.map((f) => {
                const count = f.count !== undefined ? f.count : f.predicate ? data.filter(f.predicate).length : data.length
                return (
                  <button
                    key={f.key}
                    type="button"
                    className="chip"
                    aria-pressed={currentFilterKey === f.key}
                    onClick={() => handleFilterSelect(f.key)}
                  >
                    {f.label} <span className="n">{count}</span>
                  </button>
                )
              })}
            </div>
          )}

          <div className="row items-center gap-3 flex-wrap ml-auto">
            {searchable && (
              <div className="table-search">
                <Icon name="search" size="sm" className="table-search-icon" />
                <input
                  type="text"
                  className="input input-sm table-search-input"
                  placeholder={
                    searchPlaceholder ??
                    t('common:table.searchPlaceholder', { defaultValue: 'Search...' })
                  }
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setCurrentPage(0)
                  }}
                  aria-label={
                    searchPlaceholder ??
                    t('common:table.searchAria', { defaultValue: 'Search items' })
                  }
                />
                {searchQuery && (
                  <button
                    type="button"
                    className="table-search-clear"
                    aria-label={t('common:table.clearSearch', { defaultValue: 'Clear search' })}
                    onClick={() => {
                      setSearchQuery('')
                      setCurrentPage(0)
                    }}
                  >
                    <Icon name="x" size="sm" />
                  </button>
                )}
              </div>
            )}

            {headerActions && <div className="table-actions">{headerActions}</div>}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="table-panel rt-wrap p-6 text-center muted">
          {loadingMessage ?? <p>{t('common:common.loading', { defaultValue: 'Loading...' })}</p>}
        </div>
      ) : paginatedData.length === 0 ? (
        <div className="table-panel rt-wrap p-6 text-center muted">
          {emptyMessage ?? (
            <div className="stack items-center gap-2">
              <p>{t('common:table.noResults', { defaultValue: 'No items match your search or filter.' })}</p>
              {(searchQuery || (filters && currentFilterKey !== filters[0]?.key)) && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSearchQuery('')
                    if (filters?.[0]) handleFilterSelect(filters[0].key)
                  }}
                >
                  {t('common:table.clearFilters', { defaultValue: 'Clear filters' })}
                </Button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="table-panel rt-wrap">
          <table className={`data-table rt ${tableClassName}`.trim()} aria-label={ariaLabel}>
            <thead>
              <tr>
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`${col.align === 'right' ? 'r' : ''} ${col.hideOnMobile ? 'hide-rt' : ''} ${col.className ?? ''}`.trim()}
                    data-cell={col.hideOnMobile ? 'hide' : col.wideOnMobile ? 'wide' : undefined}
                    onClick={col.sortable ? () => handleSortToggle(col) : undefined}
                    style={col.sortable ? { cursor: 'pointer' } : undefined} /* allow-raw-style: sortable header cursor */
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {col.sortable && sortKey === col.key && (
                        <Icon name={sortDir === 'asc' ? 'chevron-up' : 'chevron-down'} size="sm" />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((item, idx) => {
                const rowKey = getRowKey(item, idx)
                const isSelected = selectedRowKey === rowKey
                const customCls = rowClassName?.(item) ?? ''
                const isClickable = Boolean(onRowClick)

                return (
                  <tr
                    key={rowKey}
                    className={`${isClickable ? 'is-clickable' : ''} ${isSelected ? 'is-selected' : ''} ${customCls}`.trim()}
                    aria-selected={isSelected ? true : undefined}
                    tabIndex={isClickable ? 0 : undefined}
                    onClick={isClickable ? () => onRowClick?.(item) : undefined}
                    onKeyDown={
                      isClickable
                        ? (e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              onRowClick?.(item)
                            }
                          }
                        : undefined
                    }
                  >
                    {columns.map((col) => (
                      <td
                        key={col.key}
                        className={`${col.align === 'right' ? 'r' : ''} ${col.hideOnMobile ? 'hide-rt' : ''} ${col.className ?? ''}`.trim()}
                        data-cell={col.hideOnMobile ? 'hide' : col.wideOnMobile ? 'wide' : undefined}
                      >
                        {col.render(item, idx)}
                      </td>
                    ))}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {paginated && totalCount > 0 && (
        <div className="pager-line">
          <span>
            {rangeLabel
              ? rangeLabel(rangeStart, rangeEnd, totalCount)
              : t('common:table.showingRange', {
                  from: rangeStart,
                  to: rangeEnd,
                  total: totalCount,
                  defaultValue: `${rangeStart} to ${rangeEnd} of ${totalCount}`,
                })}
          </span>
          {totalCount > pageSize && (
            <span className="row items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage === 0}
                onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              >
                {t('common:table.previous', { defaultValue: 'Previous' })}
              </Button>
              <span className="muted small">
                {t('common:table.page', {
                  current: currentPage + 1,
                  total: totalPages,
                  defaultValue: `Page ${currentPage + 1} of ${totalPages}`,
                })}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage + 1 >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              >
                {t('common:table.next', { defaultValue: 'Next' })}
              </Button>
            </span>
          )}
        </div>
      )}

      {footer}
    </div>
  )
}
