/**
 * ProgressLine: Live progress and state indicator (spec 004, AC-004-8).
 *
 * Used for:
 * 1. Document intake progress (e.g. "Reading page 3 of 18")
 * 2. Month reconciliation status (e.g. "COLLECTING", "RECONCILING", "NEEDS_REVIEW", "RECONCILED", paused)
 */

import { forwardRef, type HTMLAttributes } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from './Badge'
import { Icon, type IconName } from './Icon'

export type ProgressStatus = 'pending' | 'running' | 'done' | 'failed' | 'paused'
export type MonthStateType = 'COLLECTING' | 'RECONCILING' | 'NEEDS_REVIEW' | 'RECONCILED' | 'SIGNED_OFF'

export interface ProgressLineProps extends HTMLAttributes<HTMLDivElement> {
  label?: string
  current?: number
  total?: number
  status?: ProgressStatus
  monthState?: MonthStateType
  note?: string | null
  showTrack?: boolean
}

function _statusIcon(status?: ProgressStatus): IconName | null {
  if (status === 'running') return 'refresh'
  if (status === 'done') return 'check-circle'
  if (status === 'failed') return 'octagon-alert'
  if (status === 'paused') return 'clock'
  return null
}

export const ProgressLine = forwardRef<HTMLDivElement, ProgressLineProps>(
  (
    {
      label,
      current,
      total,
      status,
      monthState,
      note,
      showTrack = true,
      className = '',
      ...props
    },
    ref,
  ) => {
    const { t } = useTranslation(['common'])
    const hasNumbers = current !== undefined && total !== undefined && total > 0
    const percentage = hasNumbers ? Math.min(100, Math.max(0, Math.round((current / total) * 100))) : undefined

    let displayLabel = label
    if (!displayLabel && hasNumbers) {
      displayLabel = t('common:progress.readingPage', { current, total })
    }

    const iconName = _statusIcon(status)

    const renderMonthBadge = (state: MonthStateType) => {
      switch (state) {
        case 'RECONCILING':
          return (
            <Badge variant="brand" icon={<Icon name="refresh" size="sm" />}>
              {t('common:progress.reconciling')}
            </Badge>
          )
        case 'COLLECTING':
          return (
            <Badge variant="outline" icon={<Icon name="clock" size="sm" />}>
              {t('common:progress.collecting')}
            </Badge>
          )
        case 'NEEDS_REVIEW':
          return (
            <Badge variant="medium" icon={<Icon name="circle-alert" size="sm" />}>
              {t('common:progress.needsReview')}
            </Badge>
          )
        case 'RECONCILED':
          return (
            <Badge variant="clean" icon={<Icon name="check-circle" size="sm" />}>
              {t('common:progress.reconciled')}
            </Badge>
          )
        case 'SIGNED_OFF':
          return (
            <Badge variant="clean" icon={<Icon name="check" size="sm" />}>
              {t('common:progress.signedOff')}
            </Badge>
          )
      }
    }

    return (
      <div ref={ref} className={`progress-line ${className}`} {...props}>
        <div className="progress-line-head">
          <div className="progress-line-label">
            {iconName && <Icon name={iconName} size="sm" />}
            {monthState && renderMonthBadge(monthState)}
            {displayLabel && <span>{displayLabel}</span>}
          </div>
          {percentage !== undefined && (
            <span className="progress-line-meta">{percentage}%</span>
          )}
        </div>

        {note && (
          <p className="muted small flex items-center gap-1">
            <Icon name="circle-alert" size="sm" />
            <span>{note}</span>
          </p>
        )}

        {showTrack && percentage !== undefined && (
          <div
            className="progress-track"
            role="progressbar"
            aria-valuenow={percentage}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={displayLabel || t('common:progress.label')}
          >
            <div
              className={`progress-bar ${status === 'failed' ? 'is-failed' : status === 'done' ? 'is-clean' : ''}`}
              style={{ width: `${percentage}%` }} /* allow-raw-style: progress bar width percentage */
            />
          </div>
        )}
      </div>
    )
  },
)

ProgressLine.displayName = 'ProgressLine'
