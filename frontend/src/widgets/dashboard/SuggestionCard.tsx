/**
 * Profile suggestions found in the documents (spec 014, AC-014-7): a small card that says what
 * Kredibel found, with the evidence count and a person's accept or reject. Nothing changes until
 * they decide.
 */

import { useTranslation } from 'react-i18next'
import { useDecideSuggestion, useSuggestions, type Suggestion } from '../../entities/counterparty'
import { Icon } from '../../shared/ui'

export function SuggestionCard({ items }: { items?: Suggestion[] }) {
  const { t } = useTranslation('counterparties')
  const { data } = useSuggestions('PENDING', !items)
  const decide = useDecideSuggestion()
  const open = (items ?? data?.items ?? []).filter((s) => s.status === 'PENDING' || s.status === 'CONFLICT')
  if (open.length === 0) return null
  return (
    <section className="panel" aria-labelledby="dash-suggest-h">
      <div className="panel-head">
        <h2 id="dash-suggest-h">{t('suggestions.title')}</h2>
      </div>
      <p className="small muted panel-pad" role="status">
        {t('suggestions.found', { count: open.length })}
      </p>
      <ul className="alert-list">
        {open.map((s) => (
          <li key={s.suggestionId} className="suggestion">
            <span className="kind doc">
              <Icon name="lightbulb" size="sm" />
            </span>
            <span>
              <p className="a-t">
                {t(`suggestions.fields.${s.field}`)}: {s.display}
              </p>
              <p className="a-s">
                {t(`suggestions.confidence.${s.confidence}`)}
                {s.evidence && s.evidence.length > 0 ? `, ${t('suggestions.evidence', { count: s.evidence.length })}` : ''}
                {s.status === 'CONFLICT' && s.conflictWith ? `. ${t('suggestions.conflict', { current: s.conflictWith })}` : ''}
              </p>
            </span>
            <span className="actions">
              <button
                type="button"
                className="button button-primary button-sm"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ suggestionId: s.suggestionId, decision: 'ACCEPT' })}
              >
                {t('suggestions.accept')}
              </button>
              <button
                type="button"
                className="button button-quiet button-sm"
                disabled={decide.isPending}
                onClick={() => decide.mutate({ suggestionId: s.suggestionId, decision: 'REJECT' })}
              >
                {t('suggestions.reject')}
              </button>
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
