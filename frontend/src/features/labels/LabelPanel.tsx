/**
 * The label panel (spec 016, AC-016-6, AC-016-7; docs/11 §6.11): what the AI proposed with its
 * confidence, a field to correct it, "apply to similar lines" for a category, a note, confirm or
 * save; beside it the extraction and the provenance (model, prompt, run, span, dataset use).
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type Label, useDecideLabel } from '../../entities/label'
import { formatDate, formatMonth } from '../../shared/lib/formatDate'
import { Icon } from '../../shared/ui'
import { confidenceLevel, DOC_TYPES, PAGE_TYPES, ROLES, shortModel, statusKey, valueWord } from './words'

export function Confidence({ value }: { value: number | null | undefined }) {
  const { t } = useTranslation('labels')
  const level = confidenceLevel(value)
  if (level === 'none') return <span className="conf none">{t('noScore')}</span>
  return (
    <span className={`conf ${level}`}>
      <span className="conf-bar">
        <i style={{ width: `${Math.round((value ?? 0) * 100)}%` }} /* allow-raw-style: the AI's confidence */ />
      </span>
      <span>{(value ?? 0).toFixed(2)}</span>
    </span>
  )
}

export function StatusPill({ label }: { label: Label }) {
  const { t } = useTranslation('labels')
  const key = statusKey(label)
  return (
    <span className={`lbl-status ${key}`}>
      {(key === 'verified' || key === 'corrected') && <Icon name="check" size="sm" />}
      {t(key === 'needs' ? 'status.needs' : `status.${label.status}`)}
    </span>
  )
}

export function LabelPanel({ label, onClose }: { label: Label; onClose: () => void }) {
  const { t } = useTranslation(['labels', 'months', 'documents', 'common'])
  const decide = useDecideLabel()
  const [value, setValue] = useState(label.final.value)
  const [note, setNote] = useState('')
  const [applySimilar, setApplySimilar] = useState(label.task === 'CATEGORY' && Boolean(label.subject.txId))
  const options =
    label.task === 'CATEGORY'
      ? Object.keys(t('months:categories', { returnObjects: true }) as Record<string, string>)
      : label.task === 'DOC_TYPE'
        ? DOC_TYPES
        : label.task === 'PAGE_TYPE'
          ? PAGE_TYPES
          : label.task === 'COUNTERPARTY_ROLE'
            ? ROLES
            : null
  const changed = value.trim() !== '' && value !== label.final.value
  const busy = decide.isPending
  const act = (action: 'CONFIRM' | 'CORRECT') =>
    decide.mutate({
      labelId: label.labelId,
      decision: {
        action,
        ...(action === 'CORRECT' ? { value } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
        applyToSimilar: label.task === 'CATEGORY' ? applySimilar : false,
      },
    })
  const details = [
    label.month ? t('labels:panel.month', { month: formatMonth(label.month, 'long') }) : null,
    label.subject.pageNo ? `p${label.subject.pageNo}` : null,
    label.framework && label.cashflowClass
      ? t('labels:panel.cashflow', { framework: label.framework.replace('_', ' '), cashflow: t(`months:cashflow.${label.cashflowClass}`, { defaultValue: label.cashflowClass }) })
      : null,
  ].filter(Boolean)

  return (
    <aside className="lbl-panel panel" aria-labelledby="lp-h">
      <div className="lp-main">
        <div className="lp-head">
          <span className="task">{t(`labels:tasks.${label.task}`)}</span>
          <StatusPill label={label} />
          <button type="button" className="icon-button icon-button-sm ml-auto" aria-label={t('labels:panel.close')} onClick={onClose}>
            <Icon name="x" size="sm" />
          </button>
        </div>
        <h2 id="lp-h" className="type-h3">
          {label.subject.display}
        </h2>
        {details.length > 0 && <p className="muted small">{details.join(' · ')}</p>}
        <div className="lp-ai">
          <div>
            <span className="k">{t('labels:panel.aiProposed')}</span>
            <strong>{label.ai ? valueWord(t, label.task, label.ai.value) : '—'}</strong>
            {label.status !== 'AI_PROPOSED' && (
              <span className="sub">
                {t('labels:panel.decidedBy', {
                  status: t(`labels:status.${label.status}`),
                  by: label.decidedBy ?? '',
                  when: label.decidedAt ? formatDate(label.decidedAt.slice(0, 10)) : '',
                })}
              </span>
            )}
          </div>
          <Confidence value={label.ai?.confidence} />
        </div>
        <div className="field">
          <label htmlFor="lp-value">{t(`labels:panel.correctLabel.${label.task}`)}</label>
          {options ? (
            <select id="lp-value" className="select" value={value} onChange={(e) => setValue(e.target.value)}>
              {!options.includes(value) && <option value={value}>{valueWord(t, label.task, value)}</option>}
              {options.map((option) => (
                <option key={option} value={option}>
                  {valueWord(t, label.task, option)}
                </option>
              ))}
            </select>
          ) : (
            <input id="lp-value" className="input" value={value} onChange={(e) => setValue(e.target.value)} />
          )}
        </div>
        {label.task === 'CATEGORY' && label.subject.txId && (
          <label className="check-row">
            <input type="checkbox" checked={applySimilar} onChange={(e) => setApplySimilar(e.target.checked)} /> {t('labels:panel.applySimilar')}
          </label>
        )}
        <div className="field">
          <label htmlFor="lp-note">
            {t('labels:panel.note')} <span className="muted">{t('labels:panel.noteOptional')}</span>
          </label>
          <input id="lp-note" className="input" value={note} placeholder={t('labels:panel.notePlaceholder')} onChange={(e) => setNote(e.target.value)} />
        </div>
        {decide.isError && (
          <p className="status-line bad small" role="alert">
            {decide.error.message}
          </p>
        )}
        <div className="row lp-actions">
          <button type="button" className="button button-primary" disabled={busy || changed} onClick={() => act('CONFIRM')}>
            <Icon name="check" size="sm" />
            {t(busy ? 'labels:panel.saving' : 'labels:panel.confirm')}
          </button>
          <button type="button" className="button button-secondary" disabled={busy || !changed} onClick={() => act('CORRECT')}>
            {t('labels:panel.saveCorrection')}
          </button>
        </div>
      </div>
      <div className="lp-side">
        <details className="lp-md" open>
          <summary>
            <Icon name="markdown" size="sm" />
            {t('labels:panel.extraction')}
          </summary>
          <p className="muted small">{t('labels:panel.noExtraction')}</p>
          {label.subject.docId && (
            <Link className="link small" to={`/documents/${encodeURIComponent(label.subject.docId)}`}>
              {t('labels:openPage')}
            </Link>
          )}
        </details>
        <dl className="lp-prov">
          <div>
            <dt>{t('labels:panel.model')}</dt>
            <dd>{label.ai?.model ? shortModel(label.ai.model) : '—'}</dd>
          </div>
          <div>
            <dt>{t('labels:panel.prompt')}</dt>
            <dd>{label.ai?.promptVersion ?? '—'}</dd>
          </div>
          <div>
            <dt>{t('labels:panel.run')}</dt>
            <dd>
              {label.ai?.runId ? (
                <>
                  <Link to={`/runs/${encodeURIComponent(label.ai.runId)}`}>{label.ai.runId}</Link>
                  {label.ai.spanId ? `, ${t('labels:panel.span', { span: label.ai.spanId })}` : ''}
                </>
              ) : (
                '—'
              )}
            </dd>
          </div>
          <div>
            <dt>{t('labels:panel.datasetUse')}</dt>
            <dd>{label.dataset.use === 'EXCLUDED' ? t('labels:panel.datasetExcluded') : t(`labels:dataset.${label.dataset.use}`)}</dd>
          </div>
        </dl>
      </div>
    </aside>
  )
}
