/**
 * AnswerParts component (spec 011, T011-07; AC-011-4; docs/11 §6; design/mocks/assistant.html).
 *
 * Renders structured assistant answer parts: formatted text with evidence citations chips,
 * tabular data, and mini-bars charts (CATEGORY_BREAKDOWN, MONTHLY_IN_OUT, MONEY_FLOW).
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { AnswerPart, MessageAnswer } from '../../entities/assistant'
import { Icon } from '../../shared/ui'

export interface AnswerPartsProps {
  answer?: MessageAnswer | null
}

/** Render text with citation markers [[kind:id]] converted into citation chips. */
function renderFormattedContent(text: string) {
  const parts = text.split(/(\[\[[a-zA-Z0-9_]+:[^\]]+\]\])/g)
  return parts.map((part, index) => {
    const match = part.match(/^\[\[([a-zA-Z0-9_]+):([^\]]+)\]\]$/)
    if (!match) {
      // Process bold markers **bold**
      const boldParts = part.split(/(\*\*[^*]+\*\*)/g)
      return (
        <span key={index}>
          {boldParts.map((bp, bIndex) => {
            if (bp.startsWith('**') && bp.endsWith('**')) {
              return <strong key={bIndex}>{bp.slice(2, -2)}</strong>
            }
            return bp
          })}
        </span>
      )
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
          return (
            <div
              key={idx}
              className="mini-bars"
              role="img"
              aria-label={part.chart || t('assistant:messages.assistant')}
            >
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
                  <span>{part.chart}</span>
                  <span className="bar" style={{ width: '100%' }} /* allow-raw-style: mini-bar fallback */ />
                  <b>{part.query ? JSON.stringify(part.query) : ''}</b>
                </div>
              )}

            </div>
          )
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
