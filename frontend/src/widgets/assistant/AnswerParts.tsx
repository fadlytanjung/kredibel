/**
 * AnswerParts component (spec 011, T011-07; AC-011-4; docs/11 §6; design/mocks/assistant.html).
 *
 * Renders structured assistant answer parts: formatted text with evidence citations chips,
 * markdown links to pages, tabular data, and mini-bars charts (CATEGORY_BREAKDOWN, MONTHLY_IN_OUT, MONEY_FLOW).
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { AnswerPart, MessageAnswer } from '../../entities/assistant'
import { Icon } from '../../shared/ui'

export interface AnswerPartsProps {
  answer?: MessageAnswer | null
}

/** Render markdown links and bold spans within text chunks. */
function renderMarkdownSpans(text: string) {
  // Split by markdown link pattern [label](url)
  const linkParts = text.split(/(\[[^\]]+\]\([^)]+\))/g)
  return linkParts.map((subPart, subIdx) => {
    const linkMatch = subPart.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (linkMatch) {
      const [, label, url] = linkMatch
      if (url.startsWith('/')) {
        return (
          <Link
            key={subIdx}
            to={url}
            className="link font-semibold inline-flex items-center gap-0.5 underline"
          >
            {label}
            <Icon name="arrow-up-right" size="sm" />
          </Link>
        )
      }
      return (
        <a
          key={subIdx}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="link font-semibold inline-flex items-center gap-0.5 underline"
        >
          {label}
          <Icon name="external" size="sm" />
        </a>
      )
    }

    // Process bold markers **bold**
    const boldParts = subPart.split(/(\*\*[^*]+\*\*)/g)
    return (
      <span key={subIdx}>
        {boldParts.map((bp, bIndex) => {
          if (bp.startsWith('**') && bp.endsWith('**')) {
            return <strong key={bIndex}>{bp.slice(2, -2)}</strong>
          }
          return bp
        })}
      </span>
    )
  })
}

/** Render text with citation markers [[kind:id]] converted into citation chips and markdown links. */
function renderFormattedContent(text: string) {
  const parts = text.split(/(\[\[[a-zA-Z0-9_]+:[^\]]+\]\])/g)
  return parts.map((part, index) => {
    const match = part.match(/^\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]$/)
    if (!match) {
      return <span key={index}>{renderMarkdownSpans(part)}</span>
    }

    const [, kind, id] = match
    if (kind === 'finding') {
      return (
        <Link key={index} to={`/risk/${id}`} className="citation">
          <Icon name="eye" size="sm" />
          {id}
        </Link>
      )
    }

    if (kind === 'month') {
      return (
        <Link key={index} to={`/months/${id}`} className="citation">
          <Icon name="table" size="sm" />
          {id}
        </Link>
      )
    }

    if (kind === 'doc') {
      return (
        <Link key={index} to={`/evidence/${id}`} className="citation">
          <Icon name="file-text" size="sm" />
          {id}
        </Link>
      )
    }

    return (
      <span key={index} className="citation">
        <Icon name="table" size="sm" />
        {id}
      </span>
    )
  })
}

/** Render interactive chart/diagram preview and dashboard link button. */
function ChartPart({ part }: { part: AnswerPart }) {
  const { t } = useTranslation(['assistant'])
  const isFlow = part.chart === 'MONEY_FLOW'
  const isInOut = part.chart === 'MONTHLY_IN_OUT'
  const isUnpaid = part.chart === 'INVOICE_BREAKDOWN'
  const diagramIcon = isFlow ? 'flow' : isUnpaid ? 'file-text' : 'bar-chart'
  const targetUrl = isUnpaid ? '/documents' : part.query?.month ? `/months/${String(part.query.month)}` : '/dashboard'
  const chartLabel = isFlow
    ? t('assistant:charts.moneyFlow')
    : isInOut
      ? t('assistant:charts.monthlyInOut')
      : isUnpaid
        ? t('assistant:charts.unpaidInvoices')
        : t('assistant:charts.categoryBreakdown')
  const buttonLabel = isUnpaid ? t('assistant:seeInvoicesClick') : t('assistant:seeFullDiagramClick')

  return (
    <div className="stack gap-2 my-1">
      <div className="mini-bars" role="img" aria-label={chartLabel}>
        <div className="flex items-center justify-between pb-1 border-b border-line mb-1">
          <span className="font-semibold text-xs inline-flex items-center gap-1.5">
            <Icon name={diagramIcon} size="sm" />
            <span>{chartLabel}</span>
          </span>
          <Link to={targetUrl} className="link text-xs inline-flex items-center gap-1 font-semibold">
            <span>{t('assistant:viewFullDiagram')}</span>
            <Icon name="arrow-up-right" size="sm" />
          </Link>
        </div>
        {part.rows && part.rows.length > 0 ? (
          part.rows.map(([label, val, pct], barIdx) => (
            <div key={barIdx} className="mb">
              <span>{label}</span>
              <span className="bar" style={{ width: pct || '50%' }} /* allow-raw-style: mini-bar percentage */ />
              <b>{val}</b>
            </div>
          ))
        ) : (
          <div className="mb">
            <span>{chartLabel}</span>
            <span className="bar" style={{ width: '100%' }} /* allow-raw-style: mini-bar fallback */ />
            <b>{part.query ? JSON.stringify(part.query) : ''}</b>
          </div>
        )}
      </div>
      <div className="row">
        <Link to={targetUrl} className="button button-secondary button-sm inline-flex items-center gap-1.5">
          <Icon name={diagramIcon} size="sm" />
          <span>{buttonLabel}</span>
          <Icon name="arrow-up-right" size="sm" />
        </Link>
      </div>
    </div>
  )
}

export function AnswerParts({ answer }: AnswerPartsProps) {
  const { t } = useTranslation(['assistant', 'common'])
  if (!answer || !answer.parts || answer.parts.length === 0) {
    return null
  }

  // Check if answer cites any finding or month to offer quick action buttons
  const findingCitation = answer.citations?.find((c) => c.ref.startsWith('finding:'))
  const monthCitation = answer.citations?.find((c) => c.ref.startsWith('month:'))
  const findingId = findingCitation?.ref.replace(/^finding:/, '')
  const monthVal = monthCitation?.ref.replace(/^month:/, '')

  return (
    <div className="stack gap-3">
      {answer.parts.map((part: AnswerPart, idx: number) => {
        if (part.type === 'text' && part.text) {
          return (
            <p key={idx} className="m-0 leading-relaxed whitespace-pre-line">
              {renderFormattedContent(part.text)}
            </p>
          )
        }

        if (part.type === 'table' && (part.columns || part.rows)) {
          return (
            <div key={idx} className="overflow-x-auto my-1">
              <table className="table w-full text-sm">
                {part.columns && (
                  <thead>
                    <tr>
                      {part.columns.map((c, cIdx) => (
                        <th key={cIdx} className="text-left font-semibold py-1.5 px-2 border-b border-line">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {part.rows?.map((row, rIdx) => (
                    <tr key={rIdx} className="border-b border-line last:border-b-0">
                      {row.map((cell, cellIdx) => (
                        <td key={cellIdx} className="py-1.5 px-2">
                          {renderFormattedContent(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }

        if (part.type === 'chart') {
          return <ChartPart key={idx} part={part} />
        }

        return null
      })}

      {/* Action buttons if citations exist */}
      {(findingId || monthVal) && (
        <div className="row gap-2 mt-1">
          {findingId && (
            <Link className="button button-secondary button-sm" to={`/risk/${findingId}`}>
              {t('assistant:openEvidence')}
            </Link>
          )}
          {monthVal && (
            <Link className="button button-quiet button-sm" to={`/months/${monthVal}`}>
              {t('assistant:goToMonth')}
            </Link>
          )}
        </div>
      )}
    </div>
  )
}
