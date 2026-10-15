/** A document's findings with their facts, next step and evidence (spec 006, docs/08 §1). */

import { useTranslation } from 'react-i18next'
import { evidenceFocus, type EvidenceFocus, type Finding } from './api'
import { SeverityBadge } from './SeverityBadge'

interface FindingListProps {
  findings: Finding[]
  focused?: string
  onFocus: (focus: EvidenceFocus) => void
}

export function FindingList({ findings, focused, onFocus }: FindingListProps) {
  const { t } = useTranslation('documents')
  const live = findings.filter((f) => f.status === 'OPEN' || f.status === 'ACKNOWLEDGED')
  if (live.length === 0) return <p className="muted small">{t('detail.noFindings')}</p>
  return (
    <ul className="stack gap-2">
      {live.map((f) => {
        const focus = evidenceFocus(f)
        return (
          <li key={f.findingId} className={`card p-4 stack gap-2 ${focused === f.findingId ? 'is-selected' : ''}`}>
            <div className="row items-center gap-2 flex-wrap">
              <SeverityBadge severity={f.severity} />
              <strong>{f.title}</strong>
            </div>
            {Object.keys(f.facts ?? {}).length > 0 && (
              <dl className="row gap-4 flex-wrap small">
                {Object.entries(f.facts ?? {}).map(([name, value]) => (
                  <div key={name}>
                    <dt className="muted">{t(`detail.facts.${name}`, { defaultValue: name })}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {(f.nextSteps?.length ?? 0) > 0 && <p className="small">{f.nextSteps?.[0]}</p>}
            {focus && (
              <button type="button" className="link small text-left" onClick={() => onFocus(focus)}>
                {t('detail.showOnPage', { page: focus.page })}
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}
