/**
 * ActivityTrail component (spec 011; AC-011-11).
 *
 * Displays live progress steps and tool calls during assistant reasoning.
 * Expanded while running, collapsible when completed.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { StepEvent, ToolEvent } from '../../entities/assistant/stream'
import { Icon } from '../../shared/ui'

export interface ActivityTrailProps {
  steps: StepEvent[]
  tools: ToolEvent[]
  running: boolean
}

interface ToolGroup {
  name: string
  calls: number
  args_summary?: string
  ok: boolean
}

function groupTools(tools: ToolEvent[]): ToolGroup[] {
  const groups = new Map<string, ToolGroup>()
  for (const tool of tools) {
    const existing = groups.get(tool.name)
    if (existing) {
      existing.calls += 1
      existing.args_summary = tool.args_summary
      existing.ok = tool.ok
    } else {
      groups.set(tool.name, {
        name: tool.name,
        calls: 1,
        args_summary: tool.args_summary,
        ok: tool.ok,
      })
    }
  }
  return [...groups.values()]
}

export function ActivityTrail({ steps, tools, running }: ActivityTrailProps) {
  const { t } = useTranslation(['assistant'])
  const [open, setOpen] = useState(false)

  if (!steps.length && !tools.length) return null

  const grouped = groupTools(tools)
  const openTool = running ? grouped.at(-1)?.name : undefined
  const expanded = running || open
  const currentStep = steps.at(-1)

  const headerLabel = running
    ? currentStep?.label || (openTool ? `Running ${openTool}...` : t('assistant:activity.running'))
    : `${t('assistant:activity.completed')} · ${tools.length} ${
        tools.length === 1 ? t('assistant:activity.lookup') : t('assistant:activity.lookups')
      }`

  return (
    <div
      className={`activity-trail ${running ? 'is-running' : ''}`}
      data-testid="activity-trail"
      data-running={running ? 'true' : undefined}
    >
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={expanded}
        aria-label={t('assistant:activity.toggle')}
        className="trail-head"
      >
        {running ? (
          <Icon name="spinner" className="spin" size="sm" />
        ) : (
          <Icon name="check" size="sm" />
        )}
        <span className="flex-1 truncate">{headerLabel}</span>
        <Icon name={expanded ? 'chevron-up' : 'chevron-down'} size="sm" />
      </button>

      {expanded && (
        <ul className="trail-list m-0 p-0 list-none" aria-live="polite">
          {steps.map((step, idx) => {
            const isLatest = running && idx === steps.length - 1 && !tools.length
            return (
              <li
                key={`${step.node}-${idx}`}
                className={`trail-item ${isLatest ? 'is-busy' : ''}`}
                data-testid="trail-step"
              >
                {isLatest ? (
                  <Icon name="spinner" className="spin" size="sm" />
                ) : (
                  <Icon name="check" size="sm" />
                )}
                <span>{step.label}</span>
              </li>
            )
          })}
          {grouped.map((tool) => {
            const busy = running && tool.name === openTool
            return (
              <li
                key={tool.name}
                className={`trail-item ${busy ? 'is-busy' : ''}`}
                data-testid="trail-tool"
                data-calls={tool.calls}
              >
                {busy ? (
                  <Icon name="spinner" className="spin" size="sm" />
                ) : tool.ok ? (
                  <Icon name="check" size="sm" />
                ) : (
                  <Icon name="x" size="sm" />
                )}
                <span className="font-mono">
                  {tool.name}
                  {tool.args_summary ? ` (${tool.args_summary})` : ''}
                </span>
                {tool.calls > 1 && (
                  <span className="badge badge-outline text-xs ml-auto">
                    ×{tool.calls}
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
