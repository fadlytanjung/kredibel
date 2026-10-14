import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { DuplicateDecision } from './DuplicateDecision'

const PROPS = {
  title: 'The same statement, uploaded again',
  body: 'Held until you decide.',
  sameLabel: 'Same document',
  differentLabel: 'Different',
  sameResult: 'Kept as a copy. Not read again and not counted.',
  differentResult: 'Counted as a second statement.',
  totalLabel: 'Statement total',
  baseTotal: 'IDR 18,703,918',
  countedTotal: 'IDR 24,000,000',
}

describe('DuplicateDecision (spec 018, AC-018-3)', () => {
  it('keeps the total when the copy is the same document', async () => {
    const user = userEvent.setup()
    render(<DuplicateDecision {...PROPS} />)
    expect(screen.getByText('IDR 18,703,918')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Same document' }))
    expect(screen.getByText('IDR 18,703,918')).toBeInTheDocument()
    expect(screen.queryByText('IDR 24,000,000')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Kept as a copy')
  })

  it('counts the copy and moves the total when it is a different document', async () => {
    const user = userEvent.setup()
    render(<DuplicateDecision {...PROPS} />)
    await user.click(screen.getByRole('button', { name: 'Different' }))
    expect(screen.getByText('IDR 24,000,000')).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Counted as a second statement')
  })
})
