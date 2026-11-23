/** The loan readiness report (spec 025, AC-025-4, AC-025-5; ADR-028). Synthetic data only. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import fixture from '../../../contracts/design/fixtures/readiness.json'
import { ReadinessContent } from './ReadinessPage'

let body: unknown = fixture
const server = setupServer(http.get('/api/readiness', () => HttpResponse.json(body)))
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  body = fixture
})
afterAll(() => server.close())

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <ReadinessContent />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ReadinessPage (AC-025-4)', () => {
  it('says what to fix first, with the evidence and the next step, and that it is not a credit decision', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Fix 3 things before you show a lender.' })).toBeInTheDocument()
    expect(screen.getByText('Not ready yet')).toBeInTheDocument()
    expect(screen.getByText('3 months of statements. Lenders often ask for 6: upload more.')).toBeInTheDocument()
    expect(screen.getByText('Every month is reconciled, with at least 85% of bank lines matched by Kredibel.')).toBeInTheDocument()
    const a01 = screen.getByRole('link', { name: 'August 2026: The running balance breaks after an edited amount' })
    expect(a01).toHaveAttribute('href', '/risk/fnd_a01_aug')
    expect(screen.getByRole('link', { name: /Open the review queue/ })).toHaveAttribute('href', '/review')
    expect(screen.getByText(/It is not a credit decision: the lender decides./)).toBeInTheDocument()
    const table = screen.getByRole('table')
    expect(within(table).getByText('1,004,880,250')).toBeInTheDocument()
    expect(within(table).getByText('98.0%')).toBeInTheDocument()
    expect(screen.getByText('95.2%')).toBeInTheDocument()
    expect(screen.getByText('117 sales invoices')).toBeInTheDocument()
  })

  it('prints the page', async () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => undefined)
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Print or save as PDF' }))
    expect(print).toHaveBeenCalledOnce()
    print.mockRestore()
  })

  it('AC-025-5: without a read statement it points to Documents', async () => {
    body = { ...fixture, months: [], clients: [], level: 'NOT_READY' }
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Nothing to show a lender yet' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Go to Documents' })).toHaveAttribute('href', '/documents')
    expect(screen.queryByRole('button', { name: 'Print or save as PDF' })).toBeNull()
  })
})
