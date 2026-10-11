/**
 * The Kredibel icon set: the same 24 × 24 stroke icons as the mocks (ADR-019), sized by the kit
 * classes `icon`, `icon-sm` and `icon-lg`.
 */

import { createElement } from 'react'
import { ICONS, type IconName } from './icons.generated'

export type { IconName }

export interface IconProps {
  name: IconName
  size?: 'sm' | 'md' | 'lg'
  className?: string
  /** A label makes the icon an image for screen readers; without one it is decorative. */
  label?: string
}

export function Icon({ name, size = 'md', className = '', label }: IconProps) {
  const sizeClass = size === 'sm' ? ' icon-sm' : size === 'lg' ? ' icon-lg' : ''
  const a11y = label
    ? { role: 'img' as const, 'aria-label': label }
    : { 'aria-hidden': true as const }
  return (
    <svg
      className={`icon${sizeClass}${className ? ` ${className}` : ''}`}
      viewBox="0 0 24 24"
      {...a11y}
    >
      {ICONS[name].map((element, index) => createElement(element.tag, { key: index, ...element.attrs }))}
    </svg>
  )
}
