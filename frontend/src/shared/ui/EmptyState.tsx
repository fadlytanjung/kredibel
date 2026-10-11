import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

export interface EmptyStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className = '', icon, title, description, action, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`flex flex-col items-center justify-center text-center p-8 border border-line rounded-md bg-surface ${className}`}
        {...props}
      >
        {icon && (
          <div className="w-12 h-12 mb-4 grid place-items-center rounded-sm bg-sunken text-ink-muted">
            {icon}
          </div>
        )}
        <h3 className="text-lg font-semibold text-ink mb-1">{title}</h3>
        {description && (
          <p className="text-sm text-ink-muted max-w-md mb-6">{description}</p>
        )}
        {action && <div>{action}</div>}
      </div>
    )
  }
)
EmptyState.displayName = 'EmptyState'
