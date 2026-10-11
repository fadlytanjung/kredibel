import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type ButtonHTMLAttributes } from 'react'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus cursor-pointer disabled:cursor-not-allowed disabled:bg-sunken disabled:text-ink-subtle disabled:border-transparent whitespace-nowrap',
  {
    variants: {
      variant: {
        primary: 'bg-brand text-on-brand hover:bg-brand-hover',
        secondary: 'bg-surface border border-line-strong text-ink hover:bg-sunken',
        ghost: 'bg-transparent text-brand hover:bg-brand-soft',
        quiet: 'bg-sunken text-ink hover:bg-line',
        inverse: 'bg-surface text-ink',
        accent: 'bg-brand-accent text-ink',
      },
      size: {
        sm: 'min-h-8 px-3 text-xs rounded-sm',
        md: 'min-h-10 px-4 text-sm rounded-sm',
        lg: 'min-h-12 px-5 text-base rounded-sm',
      },
      block: {
        true: 'w-full',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant, size, block, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={buttonVariants({ variant, size, block, className })}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'
