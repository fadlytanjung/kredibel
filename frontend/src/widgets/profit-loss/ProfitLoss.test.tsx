import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { apiClient } from '../../shared/api/client'
import '../../shared/i18n/setup'
import { AccountClassifications } from './AccountClassifications'
import { EMPTY_PNL, PNL, PNL_ACCOUNTS } from './fixture'
import { ProfitLossPanel, ProfitLossView } from './ProfitLossPanel'
import { AnswerParts } from '../assistant/AnswerParts'

vi.mock('../../shared/api/client', () => ({ apiClient: vi.fn() }))
afterEach(() => vi.resetAllMocks())
function setup(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<MemoryRouter><QueryClientProvider client={client}>{ui}</QueryClientProvider></MemoryRouter>)
}

it('AC-018-5: chart and table show the same money, period link and coverage', () => {
  setup(<ProfitLossView report={PNL} />)
  expect(screen.getAllByText(/IDR.*26,000,000/)[0]).toBeInTheDocument()
  expect(screen.getByText(/does not certify/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Accounts and sources' })).toHaveAttribute('href', '/profit-loss?period=2026-03')
  fireEvent.click(screen.getByRole('button', { name: 'Table' }))
  expect(screen.getByRole('cell', { name: /IDR.*26,000,000/ })).toBeInTheDocument()
})
it('AC-018-4: missing data never shows zero profit', () => {
  setup(<ProfitLossView report={EMPTY_PNL} />)
  expect(screen.getByRole('status')).toHaveTextContent('needs posted general-ledger entries')
  expect(screen.queryByText(/IDR/)).not.toBeInTheDocument()
})
it('AC-018-5: a failed request can be retried', async () => {
  vi.mocked(apiClient).mockRejectedValueOnce(new Error('offline')).mockResolvedValue(PNL)
  setup(<ProfitLossPanel period="2026-03" />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
  await screen.findByRole('alert')
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect((await screen.findAllByText('Net profit'))[0]).toBeInTheDocument()
})
it('AC-018-1: confirmation is explicit, persisted and refreshes the report', async () => {
  vi.mocked(apiClient).mockResolvedValue(PNL_ACCOUNTS)
  setup(<AccountClassifications canEdit />)
  const select = await screen.findByLabelText('Subledger')
  fireEvent.change(select, { target: { value: 'GENERAL' } })
  expect(apiClient).not.toHaveBeenCalledWith('/api/profit-loss/accounts', expect.objectContaining({ method: 'PUT' }))
  fireEvent.click(screen.getByRole('button', { name: 'Confirm classification' }))
  await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/api/profit-loss/accounts', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ accountCode: '4000', pnlLine: 'REVENUE', subledger: 'GENERAL' }) })))
  expect(await screen.findByRole('status')).toHaveTextContent('Classification confirmed')
})
it('AC-018-2: viewers have no classification action', async () => {
  vi.mocked(apiClient).mockResolvedValue(PNL_ACCOUNTS)
  setup(<AccountClassifications canEdit={false} />)
  expect(await screen.findByLabelText('Subledger')).toBeDisabled()
  expect(screen.queryByRole('button', { name: 'Confirm classification' })).not.toBeInTheDocument()
})
it('AC-018-6: assistant opens the same report period', () => {
  setup(<AnswerParts answer={{ parts: [{ type: 'chart', chart: 'PROFIT_LOSS', query: { period: '2026-Q2' } }], citations: [], toolsUsed: ['get_profit_loss'] }} />)
  expect(screen.getByRole('link', { name: 'Open profit and loss' })).toHaveAttribute('href', '/profit-loss?period=2026-Q2')
})

it('P&L flow renders Sankey and opens entries sheet on click', () => {
  setup(<ProfitLossView report={PNL} />)
  expect(screen.getByRole('button', { name: 'Flow' })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getAllByRole('button', { name: /4000 Sales/ })[0])
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.getByText('Row 1')).toBeInTheDocument()
  fireEvent.click(screen.getAllByLabelText('Close entries')[0])
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

it('AC-018-3: flow keeps revenue, other income, finance costs and tax separate', () => {
  setup(<ProfitLossView report={PNL} />)
  expect(screen.getByRole('button', { name: /4000 Sales IDR.*120,000,000/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Other income IDR.*1,000,000/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Finance costs IDR.*2,000,000/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Income tax IDR.*3,000,000/ })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /^Net profit IDR.*26,000,000/ })).toBeInTheDocument()
})

it('AC-018-5: a loss stays signed and opens only the contributing sources', () => {
  const loss = { ...PNL, currency: 'USD', lines: PNL.lines.map((line) => line.id === 'NET_PROFIT' ? { ...line, amount: '-10.25' } : line) }
  setup(<ProfitLossView report={loss} />)
  const button = screen.getByRole('button', { name: /Net profit.*10.25/ })
  expect(button).toHaveTextContent(/-.*10.25/)
  fireEvent.click(button)
  expect(screen.getByRole('dialog')).toHaveTextContent(/-.*10.25/)
  // A subtotal drawer must not add revenue and costs with the same sign.
  expect(screen.getByRole('dialog')).not.toHaveTextContent(/Total.*216,000,000/)
})

it('AC-018-5: Exact labels retain cents and large integer precision', () => {
  const amount = '9007199254740993.25'
  const report = { ...PNL, currency: 'USD', entries: [{ ...PNL.entries[0], amount }], lines: PNL.lines.map((line) => ({ ...line, amount: ['REVENUE', 'GROSS_PROFIT', 'OPERATING_PROFIT', 'NET_PROFIT'].includes(line.id) ? amount : '0' })) }
  setup(<ProfitLossView report={report} />)
  fireEvent.click(screen.getByRole('button', { name: 'Exact' }))
  expect(screen.getByRole('button', { name: /Net profit USD.*9,007,199,254,740,993.25/ })).toBeInTheDocument()
})

