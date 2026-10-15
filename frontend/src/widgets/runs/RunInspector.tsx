/**
 * The inspector for one selected call (spec 017, AC-017-6, AC-017-7): model, prompt version,
 * latency, tokens, span and trace; the labels it produced; and the content when captured, else
 * the plain sentence that it is not.
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { AgentEvent, Run } from '../../entities/run'
import { Icon } from '../../shared/ui'
import { PROMPT_OF, seconds, shortModel } from './format'
import type { SpanRow } from './spans'

export function RunInspector({ run, row, events }: { run: Run; row: SpanRow; events: AgentEvent[] }) {
  const { t } = useTranslation('runs')
  const stage = row.stage
  const event = stage ? events.find((e) => e.node === stage.node && e.spanId === stage.traceSpanId && (stage.model ? e.eventType === 'LLM_RESPONSE' : e.eventType === 'NODE_OUTPUT')) : undefined
  const labelIds = event?.labelIds ?? []
  const prompt = stage ? (run.promptVersions ?? {})[PROMPT_OF[stage.node] ?? stage.node] : undefined
  return (
    <aside className="ev-inspector panel" aria-labelledby="ev-h">
      <div className="lp-main">
        <div className="lp-head">
          <span className="task">{t(`detail.kind.${row.kind === 'wf' ? 'node' : row.kind}`)}</span>
        </div>
        <h2 id="ev-h" className="type-h3">
          {row.name}
        </h2>
        <dl className="lp-prov">
          <div>
            <dt>{t('detail.model')}</dt>
            <dd>{stage?.model ? shortModel(stage.model) : '—'}</dd>
          </div>
          <div>
            <dt>{t('detail.prompt')}</dt>
            <dd>{prompt ?? '—'}</dd>
          </div>
          <div>
            <dt>{t('detail.latency')}</dt>
            <dd>{seconds(row.end - row.start)}</dd>
          </div>
          <div>
            <dt>{t('detail.tokens')}</dt>
            <dd>{stage?.model ? t('detail.tokensValue', { tokensIn: (stage.tokensIn ?? 0).toLocaleString('en'), tokensOut: (stage.tokensOut ?? 0).toLocaleString('en') }) : '—'}</dd>
          </div>
          <div>
            <dt>{t('detail.span')}</dt>
            <dd>{stage?.traceSpanId ? t('detail.spanValue', { span: stage.traceSpanId, trace: `${(run.traceId ?? '').slice(0, 4)}…` }) : '—'}</dd>
          </div>
        </dl>
        <div className="row">
          {labelIds.length > 0 && (
            <Link className="button button-secondary button-sm" to={`/labels/${encodeURIComponent(labelIds[0])}`}>
              <Icon name="tag" size="sm" />
              {t('detail.openLabel')}
            </Link>
          )}
          {run.traceUrl && (
            <a className="button button-quiet button-sm" href={run.traceUrl} target="_blank" rel="noreferrer">
              <Icon name="external" size="sm" />
              {t('detail.cloudTrace')}
            </a>
          )}
        </div>
      </div>
      <div className="lp-side">
        <p className="muted small">{t('detail.notCaptured')}</p>
      </div>
    </aside>
  )
}
