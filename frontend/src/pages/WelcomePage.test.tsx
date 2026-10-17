/** The welcome question after onboarding (spec 024, AC-024-4). Synthetic data only. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import type { Workspace } from '../entities/workspace'
import { WelcomePage } from './WelcomePage'

const WORKSPACE = {
  orgId: 'org_1',
  name: 'Synthetic Roasters Ltd',
  entityType: 'COMPANY',
  country: 'ID',
  timezone: 'Asia/Jakarta',
  currency: 'IDR',
  defaultLanguage: 'en',
  subscription: { planId: 'free_trial', status: 'TRIAL' },
  expectations: [],
} as unknown as Workspace

let patched: Record<string, unknown> | null = null
const server = setupServer(
  http.get('/api/workspace', () => HttpResponse.json(WORKSPACE)),
  http.patch('/api/workspace', async ({ request }) => {
    patched = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ ...WORKSPACE, ...patched })
  }),
)
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  patched = null
})
afterAll(() => server.close())

function renderWelcome(entry = '/welcome') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/welcome" element={<WelcomePage />} />
          <Route path="/dashboard" element={<p>dashboard</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return userEvent.setup()
}

describe('WelcomePage (AC-024-4)', () => {
  it('keeping the books saves the goal and opens the dashboard', async () => {
    const user = renderWelcome()
    await user.click(await screen.findByRole('button', { name: /Keep my books/ }))
    expect(await screen.findByText('dashboard')).toBeInTheDocument()
    expect(patched).toEqual({ goal: 'BOOKKEEPING' })
  })

  it('skipping keeps the books, so the question is not asked again', async () => {
    const user = renderWelcome()
    await user.click(await screen.findByRole('button', { name: 'Skip for now' }))
    expect(await screen.findByText('dashboard')).toBeInTheDocument()
    expect(patched).toEqual({ goal: 'BOOKKEEPING' })
  })

  it('expectations are written per month and saved as decimal strings', async () => {
    const user = renderWelcome()
    const expect_ = await screen.findByRole('button', { name: /Check what I expect/ })
    await user.click(expect_)
    expect(expect_).toHaveAttribute('aria-expanded', 'true')

    const month = screen.getByLabelText('Month')
    await user.clear(month)
    await user.type(month, '2026-08')
    await user.type(screen.getByLabelText('Money in'), '150.000.000x')
    await user.click(screen.getByRole('button', { name: 'Save and go to my dashboard' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('at least one amount as digits')
    expect(patched).toBeNull()

    await user.clear(screen.getByLabelText('Money in'))
    await user.type(screen.getByLabelText('Money in'), '150.000.000')
    await user.type(screen.getByLabelText('Money out'), '120000000')
    await user.click(screen.getByRole('button', { name: 'Save and go to my dashboard' }))
    await waitFor(() =>
      expect(patched).toEqual({
        goal: 'CHECK_EXPECTATIONS',
        expectations: [{ month: '2026-08', moneyIn: '150000000.00', moneyOut: '120000000.00' }],
      }),
    )
    expect(await screen.findByText('dashboard')).toBeInTheDocument()
  })
})
