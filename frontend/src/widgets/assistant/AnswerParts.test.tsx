import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { MessageAnswer } from '../../entities/assistant'
import { AnswerParts } from './AnswerParts'

describe('AnswerParts', () => {
  it('renders text with citations and bold markup', () => {
    const answer: MessageAnswer = {
      parts: [
        {
          type: 'text',
          text: 'You paid Green Valley Farms **IDR 56,050,000** in March [[finding:A01]].',
        },
      ],
      citations: [{ ref: 'finding:A01', label: 'Finding A01' }],
      grounding: { verdict: 'AGREED', citations: ['finding:A01'] },
      toolsUsed: ['get_period_summary'],
    }

    render(
      <MemoryRouter>
        <AnswerParts answer={answer} />
      </MemoryRouter>,
    )

    expect(screen.getByText('IDR 56,050,000')).toBeInTheDocument()
    // The chip carries the citation's label, not the bare ID (mock assistant.html).
    expect(screen.getByRole('link', { name: 'Finding A01' })).toHaveAttribute('href', '/risk/A01')
    expect(screen.getByText('Open the evidence')).toBeInTheDocument()
  })

  it('renders markdown links to internal pages', () => {
    const answer: MessageAnswer = {
      parts: [
        {
          type: 'text',
          text: 'See the [Cash Flow Dashboard](/dashboard) and [May 2026](/months/2026-05) for details.',
        },
      ],
      citations: [],
      grounding: { verdict: 'AGREED', citations: [] },
      toolsUsed: [],
    }

    render(
      <MemoryRouter>
        <AnswerParts answer={answer} />
      </MemoryRouter>,
    )

    const dashLink = screen.getByRole('link', { name: /Cash Flow Dashboard/i })
    expect(dashLink).toBeInTheDocument()
    expect(dashLink).toHaveAttribute('href', '/dashboard')

    const monthLink = screen.getByRole('link', { name: /May 2026/i })
    expect(monthLink).toBeInTheDocument()
    expect(monthLink).toHaveAttribute('href', '/months/2026-05')
  })

  it('renders tabular parts correctly', () => {
    const answer: MessageAnswer = {
      parts: [
        {
          type: 'table',
          columns: ['Date', 'Amount', 'Description'],
          rows: [
            ['5 Mar', 'IDR 32,100,000', 'Transfer 1'],
            ['12 Mar', 'IDR 9,850,000', 'Transfer 2'],
          ],
        },
      ],
      citations: [],
      grounding: { verdict: 'AGREED', citations: [] },
      toolsUsed: [],
    }

    render(
      <MemoryRouter>
        <AnswerParts answer={answer} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByText('Transfer 1')).toBeInTheDocument()
    expect(screen.getByText('Transfer 2')).toBeInTheDocument()
  })

  it('renders chart mini-bars and diagram link button correctly', () => {
    const answer: MessageAnswer = {
      parts: [
        {
          type: 'chart',
          chart: 'MONEY_FLOW',
          rows: [
            ['Rent', 'IDR 15,000,000', '60%'],
            ['Payroll', 'IDR 10,000,000', '40%'],
          ],
        },
      ],
      citations: [],
      grounding: { verdict: 'AGREED', citations: [] },
      toolsUsed: [],
    }

    render(
      <MemoryRouter>
        <AnswerParts answer={answer} />
      </MemoryRouter>,
    )

    expect(screen.getByRole('img', { name: 'Money Flow (Sankey)' })).toBeInTheDocument()
    expect(screen.getByText('Rent')).toBeInTheDocument()
    expect(screen.getByText('IDR 15,000,000')).toBeInTheDocument()
    expect(screen.getByText('Money Flow (Sankey)')).toBeInTheDocument()
    expect(screen.getByText('See full interactive diagram on Dashboard')).toBeInTheDocument()
  })
})
