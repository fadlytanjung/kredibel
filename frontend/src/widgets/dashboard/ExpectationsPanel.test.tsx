/** What the person expected against the reconciled months (spec 024, AC-024-5). Synthetic data only. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter } from 'react-router-dom'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { ExpectationsPanel } from './ExpectationsPanel'

const server = setupServer(
  http.get('/api/expectations', () =>
    HttpResponse.json({
      tolerance: '0.05',
      months: [
        {
          month: '2026-08',
          moneyIn: { expected: '160000000.00', actual: '160423200.00', difference: '423200.00', status: 'AS_EXPECTED' },
          moneyOut: { expected: '120000000.00', actual: '152306418.00', difference: '32306418.00', status: 'DIFFERENT' },
        },
        { month: '2026-09', moneyIn: { expected: '150000000.00', actual: null, difference: null, status: 'WAITING' }, moneyOut: null },
      ],
    }),
  ),
)
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())

describe('ExpectationsPanel (AC-024-5)', () => {
  it('shows each month as expected, different by an amount, or waiting, with the way to its records', async () => {
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <ExpectationsPanel currency="IDR" />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByRole('heading', { name: 'What you expected' })).toBeInTheDocument()
    expect(screen.getByText('Your expectations against the reconciled months, in IDR. Within 5% counts as expected.')).toBeInTheDocument()
    const [aug, sep] = screen.getAllByRole('listitem')
    expect(within(aug).getByText('As expected')).toBeInTheDocument()
    expect(within(aug).getByText(/32,306,418 more than expected/)).toBeInTheDocument()
    expect(within(aug).getByRole('link', { name: 'Open the month' })).toHaveAttribute('href', '/months/2026-08')
    expect(within(aug).getByRole('link', { name: 'Documents' })).toHaveAttribute('href', '/documents?month=2026-08')
    expect(within(sep).getByText("Waiting for this month's documents")).toBeInTheDocument()
    expect(within(sep).queryByText('Money out')).toBeNull()
  })
})
