import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'

export interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  message: ReactNode
  icon?: ReactNode
  onClose?: () => void
}

export const Toast = forwardRef<HTMLDivElement, ToastProps>(
  ({ className = '', message, icon, onClose, ...props }, ref) => {
    return (
      <div
        ref={ref}
        role="status"
        aria-live="polite"
        className={`inline-flex items-center gap-3 px-4 py-3 rounded-md bg-inverse text-on-inverse shadow-overlay text-sm font-medium ${className}`}
        {...props}
      >
        {icon && <span className="flex-none">{icon}</span>}
        <span className="flex-1 min-w-0">{message}</span>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="flex-none p-1 rounded-xs hover:bg-surface/20 transition-colors cursor-pointer"
            aria-label="Close"
          >
            ×
          </button>
        )}
      </div>
    )
  }
)
Toast.displayName = 'Toast'
