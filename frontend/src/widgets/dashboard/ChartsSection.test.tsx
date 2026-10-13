import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../../shared/api/client'
import { CASH, FLOW_PARTIES, FLOW_STATEMENT, LINES } from './charts.fixture'
import { ChartsSection } from './ChartsSection'

vi.mock('../../shared/api/client', () => ({ apiClient: vi.fn(), ProblemError: class ProblemError extends Error {} }))

function serve(cash: unknown = CASH) {
  vi.mocked(apiClient).mockImplementation((url: string) => {
    if (url.startsWith('/api/money-flow')) return Promise.resolve(url.includes('COUNTERPARTIES') ? FLOW_PARTIES : FLOW_STATEMENT)
    if (url.startsWith('/api/cash-flow')) return Promise.resolve(cash)
    if (url.startsWith('/api/bank-lines')) return Promise.resolve(LINES)
    return Promise.resolve({})
  })
}

describe('ChartsSection (T010-05)', () => {
  let client: QueryClient
  beforeEach(() => {
    client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.clearAllMocks()
  })
  const renderIt = () =>
    render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <ChartsSection period="all" range="February to April 2026" framework="IFRS" />
        </QueryClientProvider>
      </MemoryRouter>,
    )

  it('draws the money flow with labels and amounts in millions (AC-010-5, AC-010-6)', async () => {
    serve()
    renderIt()
    const flow = await screen.findByRole('region', { name: 'Money flow' })
    await waitFor(() => expect(within(flow).getAllByRole('img').length).toBeGreaterThan(0))
    const [sankey] = within(flow).getAllByRole('img')
    expect(within(sankey).getByRole('button', { name: 'Harborview Hotel Group 331.0' })).toBeInTheDocument()
    expect(within(sankey).getByRole('button', { name: /Operating to Payroll: 257\.6, 6 bank lines/ })).toBeInTheDocument()
    expect(within(flow).getByText('Amounts in millions.')).toBeInTheDocument()
    expect(apiClient).toHaveBeenCalledWith('/api/money-flow?period=all&view=STATEMENT&framework=IFRS')
  })

  it('a band opens its bank lines with their exact total (AC-010-6)', async () => {
    serve()
    renderIt()
    const flow = await screen.findByRole('region', { name: 'Money flow' })
    await waitFor(() => expect(within(flow).getAllByRole('img').length).toBeGreaterThan(0))
    const [sankey] = within(flow).getAllByRole('img')
    fireEvent.click(within(sankey).getByRole('button', { name: /Harborview Hotel Group to Archipelago/ }))
    const sheet = await screen.findByRole('dialog')
    expect(await within(sheet).findByText('2 bank lines, IDR 100,150,000 in all')).toBeInTheDocument()
    expect(apiClient).toHaveBeenCalledWith(expect.stringContaining('/api/bank-lines?flow=src%3Aclient%3Aharbor%3Eacc%3Aacb'))
    fireEvent.click(within(sheet).getByRole('button', { name: 'Close' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('switches views and frameworks without touching the workspace setting (AC-010-7, AC-010-12)', async () => {
    serve()
    renderIt()
    const flow = await screen.findByRole('region', { name: 'Money flow' })
    fireEvent.click(within(flow).getByRole('button', { name: 'Table' }))
    expect(await within(flow).findByRole('cell', { name: 'Payroll' })).toBeInTheDocument()
    fireEvent.click(within(flow).getByRole('button', { name: 'By client and supplier' }))
    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/api/money-flow?period=all&view=COUNTERPARTIES&framework=IFRS'))
    fireEvent.click(screen.getByRole('button', { name: 'US GAAP' }))
    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/api/money-flow?period=all&view=COUNTERPARTIES&framework=US_GAAP'))
    expect(apiClient).not.toHaveBeenCalledWith(expect.stringContaining('/api/workspace'), expect.objectContaining({ method: 'PATCH' }))
  })

  it('outlines risky months and draws the cash-flow statement (AC-010-13, AC-010-14)', async () => {
    serve()
    renderIt()
    expect(await screen.findByText('Net above each pair. Outlined: March, with a high or critical risk.')).toBeInTheDocument()
    const statement = screen.getByRole('region', { name: 'Cash-flow statement' })
    const [waterfall] = within(statement).getAllByRole('img')
    expect(within(waterfall).getByText('Opening balance')).toBeInTheDocument()
    expect(within(waterfall).getByText('-50.7')).toBeInTheDocument()
    expect(within(waterfall).getByText('164.4')).toBeInTheDocument()
  })

  it('names what is missing instead of a waterfall that does not add up (AC-010-14)', async () => {
    serve({ ...CASH, balanced: false, gaps: [{ kind: 'MISSING_MONTH', month: '2026-03', account: 'Archipelago Commerce Bank ••••4821' }] })
    renderIt()
    const statement = await screen.findByRole('region', { name: 'Cash-flow statement' })
    expect(within(statement).getByText('Archipelago Commerce Bank ••••4821 has no statement for March 2026.')).toBeInTheDocument()
    expect(within(statement).queryByRole('img')).not.toBeInTheDocument()
  })
})
