/**
 * Profile suggestions found in the documents (spec 014, AC-014-7): a small card that says what
 * Kredibel found, where it came from (a link to the document), and a person's accept or reject.
 * Nothing changes until they decide. On the dashboard the card points to Profile settings, its
 * home, and hides when nothing is open; in settings it says so instead.
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useDecideSuggestion, useSuggestions, type Suggestion } from '../../entities/counterparty'
import { Icon } from '../../shared/ui'

export function SuggestionCard({ items, place = 'dashboard' }: { items?: Suggestion[]; place?: 'dashboard' | 'settings' }) {
  const { t } = useTranslation('counterparties')
  const { data } = useSuggestions('PENDING', !items)
  const decide = useDecideSuggestion()
  const open = (items ?? data?.items ?? []).filter((s) => s.status === 'PENDING' || s.status === 'CONFLICT')
  if (open.length === 0 && place === 'dashboard') return null
  return (
    <section className="panel" aria-labelledby="dash-suggest-h">
      <div className="panel-head">
        <h2 id="dash-suggest-h">{t('suggestions.title')}</h2>
        {place === 'dashboard' && (
          <Link className="link" to="/settings/profile">
            {t('suggestions.settings')}
          </Link>
        )}
      </div>
      {open.length === 0 ? (
        <p className="small muted panel-pad">
          {t('suggestions.none')}
        </p>
      ) : (
        <p className="small muted panel-pad">
          {t('suggestions.found', { count: open.length })}
        </p>
      )}
      {open.length > 0 && (
        <ul className="alert-list">
          {open.map((s) => {
            const count = s.evidence?.length ?? 0
            const from = s.evidence?.find((e) => e.docId)?.docId
            return (
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
                    {count > 0 && (
                      <>
                        {', '}
                        {from ? (
                          <Link to={`/documents/${encodeURIComponent(from)}`}>{t('suggestions.evidence', { count })}</Link>
                        ) : (
                          t('suggestions.evidence', { count })
                        )}
                      </>
                    )}
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
            )
          })}
        </ul>
      )}
    </section>
  )
}
