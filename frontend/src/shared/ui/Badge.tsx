import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

/** kit.css `.badge` and its modifiers (ADR-019). */
export const badgeVariants = cva('badge', {
  variants: {
    variant: {
      default: '',
      critical: 'badge-critical',
      high: 'badge-high',
      medium: 'badge-medium',
      low: 'badge-low',
      clean: 'badge-clean',
      tampered: 'badge-tampered',
      brand: 'badge-brand',
      evidence: 'badge-evidence',
      outline: 'badge-outline',
    },
    status: {
      true: 'badge-status',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  icon?: ReactNode
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant, status, icon, children, ...props }, ref) => (
    <span ref={ref} className={badgeVariants({ variant, status, className })} {...props}>
      {icon}
      {children}
    </span>
  ),
)
Badge.displayName = 'Badge'
