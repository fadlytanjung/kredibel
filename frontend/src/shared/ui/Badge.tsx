import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

export const badgeVariants = cva(
  'inline-flex items-center gap-1.5 h-6 px-2 rounded-xs text-xs font-semibold leading-none whitespace-nowrap',
  {
    variants: {
      variant: {
        default: 'bg-sunken text-ink',
        critical: 'bg-critical-soft text-critical',
        high: 'bg-high-soft text-high',
        medium: 'bg-medium-soft text-medium',
        low: 'bg-low-soft text-low',
        clean: 'bg-clean-soft text-clean',
        tampered: 'bg-tampered-soft text-tampered',
        brand: 'bg-brand-soft text-brand',
        evidence: 'bg-evidence-soft text-evidence-text',
        outline: 'bg-transparent border border-line-strong text-ink-muted',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  icon?: ReactNode
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant, icon, children, ...props }, ref) => {
    return (
      <span ref={ref} className={badgeVariants({ variant, className })} {...props}>
        {icon}
        {children}
      </span>
    )
  }
)
Badge.displayName = 'Badge'
