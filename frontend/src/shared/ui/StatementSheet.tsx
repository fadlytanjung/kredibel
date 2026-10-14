import type { ReactNode } from 'react'

/**
 * A printed statement surface (spec 018): a bank header, optional content (the read-twice scene or a
 * held row), the rows and the closing balance. Values keep their provenance reading mark (docs/12
 * §6.1). Presentational only.
 */
export type Reading = 'AGREED' | 'SINGLE_SOURCE' | 'CONFLICT'

export interface StatementRow {
  date: string
  text: string
  amount?: string
  held?: boolean
  reading?: Reading
}

export interface StatementSheetProps {
  bank: string
  meta: string
  rows: StatementRow[]
  balanceLabel: string
  balance: string
  heldLabel: string
  children?: ReactNode
}

const READING_CLASS: Record<Reading, string> = {
  AGREED: 'reading reading-agreed',
  SINGLE_SOURCE: 'reading reading-single',
  CONFLICT: 'reading reading-conflict',
}

export function StatementSheet({
  bank,
  meta,
  rows,
  balanceLabel,
  balance,
  heldLabel,
  children,
}: StatementSheetProps) {
  return (
    <div className="statement-sheet">
      <div className="statement-head">
        <span className="bank">
          <i aria-hidden="true" />
          {bank}
        </span>
        <span className="meta">{meta}</span>
      </div>
      {children}
      <div className="statement-rows">
        {rows.map((row) => (
          <div className={`statement-row${row.held ? ' is-held' : ''}`} key={`${row.date}-${row.text}`}>
            <span className="d">{row.date}</span>
            <span className="desc">{row.text}</span>
            <span className={`amt${row.reading ? ` ${READING_CLASS[row.reading]}` : ''}`}>
              {row.amount ?? heldLabel}
            </span>
          </div>
        ))}
      </div>
      <div className="statement-foot">
        <span>{balanceLabel}</span>
        <span className="total">{balance}</span>
      </div>
    </div>
  )
}
