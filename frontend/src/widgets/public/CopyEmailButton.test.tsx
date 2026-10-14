import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CopyEmailButton } from './CopyEmailButton'

function renderButton() {
  return render(
    <CopyEmailButton email="hello@kredibel.app" label="Copy address" copied="Address copied" failed="Could not copy" />,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('CopyEmailButton (spec 018, AC-018-7)', () => {
  it('copies the address and says so in a live region', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    renderButton()
    expect(screen.getByRole('status')).toHaveTextContent('')
    await user.click(screen.getByRole('button', { name: 'Copy address' }))
    expect(writeText).toHaveBeenCalledWith('hello@kredibel.app')
    expect(screen.getByRole('status')).toHaveTextContent('Address copied')
  })

  it('says when the browser will not copy, without a text field', async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: () => Promise.reject(new Error('denied')) },
      configurable: true,
    })
    renderButton()
    await user.click(screen.getByRole('button', { name: 'Copy address' }))
    expect(screen.getByRole('status')).toHaveTextContent('Could not copy')
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })
})
