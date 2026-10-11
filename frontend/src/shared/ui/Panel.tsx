import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

export const panelVariants = cva(
  'border border-line rounded-md bg-surface text-ink overflow-hidden',
  {
    variants: {
      elevation: {
        flat: '',
        raised: 'shadow-raised bg-raised',
        overlay: 'shadow-overlay bg-raised',
      },
    },
    defaultVariants: {
      elevation: 'flat',
    },
  }
)

export interface PanelProps
  extends Omit<HTMLAttributes<HTMLDivElement>, 'title'>,
    VariantProps<typeof panelVariants> {
  title?: ReactNode
  action?: ReactNode
  padded?: boolean
}

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ className = '', elevation, title, action, padded = true, children, ...props }, ref) => {
    return (
      <div ref={ref} className={panelVariants({ elevation, className })} {...props}>
        {(title || action) && (
          <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-line">
            {typeof title === 'string' ? (
              <h2 className="text-base font-semibold leading-normal">{title}</h2>
            ) : (
              title
            )}
            {action}
          </div>
        )}
        <div className={padded ? 'p-5' : ''}>{children}</div>
      </div>
    )
  }
)
Panel.displayName = 'Panel'
