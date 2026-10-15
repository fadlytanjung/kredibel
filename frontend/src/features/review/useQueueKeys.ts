/** Keyboard for the review queue (AC-009-7, docs/11 §6.5): J and K next and previous, Enter the
 * primary action, Esc close. Ignored while typing, and Enter is left to a focused button or link. */

import { useEffect } from 'react'

export interface QueueKeys {
  next?: () => void
  previous?: () => void
  primary?: () => void
  close?: () => void
}

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}

export function useQueueKeys(keys: QueueKeys) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey || typing(event.target)) return
      const target = event.target instanceof HTMLElement ? event.target : null
      const handler =
        event.key === 'j' || event.key === 'J'
          ? keys.next
          : event.key === 'k' || event.key === 'K'
            ? keys.previous
            : event.key === 'Escape'
              ? keys.close
              : event.key === 'Enter' && !target?.closest('button, a')
                ? keys.primary
                : undefined
      if (!handler) return
      event.preventDefault()
      handler()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [keys])
}
