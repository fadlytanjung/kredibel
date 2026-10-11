import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

/** kit.css `.panel` with an optional `.panel-head` (ADR-019). */
export interface PanelProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode
  action?: ReactNode
  padded?: boolean
}

export const Panel = forwardRef<HTMLDivElement, PanelProps>(
  ({ className = '', title, action, padded = true, children, ...props }, ref) => (
    <div ref={ref} className={`panel${className ? ` ${className}` : ''}`} {...props}>
      {(title || action) && (
        <div className="panel-head">
          {typeof title === 'string' ? <h2>{title}</h2> : title}
          {action}
        </div>
      )}
      <div className={padded ? 'panel-pad' : undefined}>{children}</div>
    </div>
  ),
)
Panel.displayName = 'Panel'
