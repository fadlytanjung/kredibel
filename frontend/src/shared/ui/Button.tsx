import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'

/** kit.css `.button` and its modifiers (ADR-019). `plain` is the bare button (disabled plan cards). */
export const buttonVariants = cva('button', {
  variants: {
    variant: {
      primary: 'button-primary',
      secondary: 'button-secondary',
      ghost: 'button-ghost',
      quiet: 'button-quiet',
      inverse: 'button-inverse',
      accent: 'button-accent',
      plain: '',
    },
    size: {
      sm: 'button-sm',
      md: '',
      lg: 'button-lg',
    },
    block: {
      true: 'button-block',
    },
  },
  defaultVariants: {
    variant: 'primary',
    size: 'md',
  },
})

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant, size, block, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={buttonVariants({ variant, size, block, className })}
      {...props}
    />
  ),
)
Button.displayName = 'Button'
