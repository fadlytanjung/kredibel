/**
 * Form fields in the kit's vocabulary: `.field`, `.input`, `.select`, `.hint` (ADR-019). Errors use
 * the same hint line in the critical colour and are tied to the control with aria-describedby.
 */

import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react'

export interface FieldProps {
  id: string
  label: ReactNode
  hint?: ReactNode
  error?: string
  className?: string
  children: ReactNode
}

export function Field({ id, label, hint, error, className = '', children }: FieldProps) {
  return (
    <div className={`field${className ? ` ${className}` : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {error ? (
        <span id={`${id}-error`} className="hint text-critical" role="alert">
          {error}
        </span>
      ) : (
        hint && <span className="hint">{hint}</span>
      )}
    </div>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className = '', ...props }, ref) => (
    <input ref={ref} className={`input aria-invalid:border-critical${className ? ` ${className}` : ''}`} {...props} />
  ),
)
Input.displayName = 'Input'

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className = '', ...props }, ref) => (
    <select ref={ref} className={`select aria-invalid:border-critical${className ? ` ${className}` : ''}`} {...props} />
  ),
)
Select.displayName = 'Select'
