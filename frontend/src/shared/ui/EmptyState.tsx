import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

/** Built from kit pieces (`.panel`, `.panel-pad`, `.stack`, type classes); the mocks have no empty
 *  screen, so it follows docs/11 §7: say what will appear and the action that creates it. */
export interface EmptyStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
}

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className = '', icon, title, description, action, ...props }, ref) => (
    <div
      ref={ref}
      className={`panel panel-pad stack gap-4 items-center text-center py-12${className ? ` ${className}` : ''}`}
      {...props}
    >
      {icon && (
        <span className="grid place-items-center w-12 h-12 rounded-md bg-brand-soft text-brand">
          {icon}
        </span>
      )}
      <div className="stack gap-2 items-center">
        <h2 className="type-h2">{title}</h2>
        {description && <p className="muted max-w-md">{description}</p>}
      </div>
      {action}
    </div>
  ),
)
EmptyState.displayName = 'EmptyState'
