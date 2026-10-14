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
    expect(screen.getByText('A01')).toBeInTheDocument()
    expect(screen.getByText('Open the evidence')).toBeInTheDocument()
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

  it('renders chart mini-bars correctly', () => {
    const answer: MessageAnswer = {
      parts: [
        {
          type: 'chart',
          chart: 'CATEGORY_BREAKDOWN',
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

    expect(screen.getByRole('img', { name: 'CATEGORY_BREAKDOWN' })).toBeInTheDocument()
    expect(screen.getByText('Rent')).toBeInTheDocument()
    expect(screen.getByText('IDR 15,000,000')).toBeInTheDocument()
  })
})
