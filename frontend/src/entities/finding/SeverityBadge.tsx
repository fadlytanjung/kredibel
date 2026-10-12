/**
 * Severity badge showing colour + icon + text (spec 008, AC-008-10, NFR-08).
 */

import { forwardRef, type HTMLAttributes } from 'react'
import { useTranslation } from 'react-i18next'
import { Badge } from '../../shared/ui/Badge'
import { Icon, type IconName } from '../../shared/ui/Icon'

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'

const SEVERITY_CONFIG: Record<
  SeverityLevel,
  {
    variant: 'critical' | 'high' | 'medium' | 'low' | 'default'
    icon: IconName
  }
> = {
  CRITICAL: { variant: 'critical', icon: 'octagon-alert' },
  HIGH: { variant: 'high', icon: 'triangle-alert' },
  MEDIUM: { variant: 'medium', icon: 'circle-alert' },
  LOW: { variant: 'low', icon: 'info' },
  INFO: { variant: 'default', icon: 'info' },
}

export interface SeverityBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  severity: SeverityLevel
  status?: boolean
  showText?: boolean
}

export const SeverityBadge = forwardRef<HTMLSpanElement, SeverityBadgeProps>(
  ({ severity, status, showText = true, className = '', ...props }, ref) => {
    const { t } = useTranslation('risk')
    const config = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.INFO
    const text = t(`severity.${severity}`, { defaultValue: severity })

    return (
      <Badge
        ref={ref}
        variant={config.variant}
        status={status}
        icon={<Icon name={config.icon} size="sm" />}
        className={className}
        data-severity={severity}
        {...props}
      >
        {showText && text}
      </Badge>
    )
  },
)

SeverityBadge.displayName = 'SeverityBadge'
