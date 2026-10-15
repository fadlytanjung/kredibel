import { useState } from 'react'
import { Icon } from '../../shared/ui'

/**
 * Copy the contact address (spec 020, AC-020-7): one button and a polite status, no form and no text
 * field. If the browser refuses the clipboard the status says so and the address stays selectable.
 */
export interface CopyEmailButtonProps {
  email: string
  label: string
  copied: string
  failed: string
}

export function CopyEmailButton({ email, label, copied, failed }: CopyEmailButtonProps) {
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle')

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(email)
      setState('copied')
    } catch {
      setState('failed')
    }
  }

  return (
    <>
      <button type="button" className="button button-lg pub-ghost" onClick={() => void copy()}>
        <Icon name="copy" size="sm" />
        {label}
      </button>
      <span className="pub-copy-status" role="status" aria-live="polite">
        {state === 'copied' ? copied : state === 'failed' ? failed : ''}
      </span>
    </>
  )
}
