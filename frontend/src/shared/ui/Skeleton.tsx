import { cva, type VariantProps } from 'class-variance-authority'
import { forwardRef, type HTMLAttributes } from 'react'

export const skeletonVariants = cva('animate-pulse bg-sunken', {
  variants: {
    variant: {
      text: 'h-4 w-full rounded-xs',
      rectangular: 'rounded-sm',
      circular: 'rounded-full',
    },
  },
  defaultVariants: {
    variant: 'rectangular',
  },
})

export interface SkeletonProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className = '', variant, ...props }, ref) => {
    return <div ref={ref} className={skeletonVariants({ variant, className })} {...props} />
  }
)
Skeleton.displayName = 'Skeleton'
