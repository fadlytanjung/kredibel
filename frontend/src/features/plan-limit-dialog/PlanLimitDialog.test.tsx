import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../../shared/api/client'
import { PlanLimitDialog, PlanLimitProvider } from './PlanLimitDialog'

const server = setupServer()
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('PlanLimitDialog (AC-013-13)', () => {
  it('renders the limit, usage and maximum and navigates to plan settings', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <PlanLimitDialog
          problem={{ limit: 'extractedPagesPerMonth', used: 400, max: 400 }}
          onClose={onClose}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText('You have reached a plan limit')).toBeInTheDocument()
    expect(screen.getByText(/400 of 400 pages read this month used/)).toBeInTheDocument()

    const link = screen.getByRole('link', { name: 'See plan and usage' })
    expect(link).toHaveAttribute('href', '/settings/plan')

    const closeBtn = screen.getAllByRole('button', { name: 'Close' })[1]
    await user.click(closeBtn)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes when Escape is pressed', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <PlanLimitDialog
          problem={{ limit: 'documentsPerMonth', used: 150, max: 150 }}
          onClose={onClose}
        />
      </MemoryRouter>,
    )

    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
  })
})

describe('PlanLimitProvider', () => {
  it('opens the dialog when a PLAN_LIMIT_REACHED problem is dispatched', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <PlanLimitProvider>
            <div>Test child content</div>
          </PlanLimitProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(screen.getByText('Test child content')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()

    // Trigger problem via failing endpoint
    server.use(
      http.get('/api/trigger-limit', () =>
        HttpResponse.json(
          {
            type: 'about:blank',
            title: 'Plan limit reached',
            status: 403,
            code: 'PLAN_LIMIT_REACHED',
            limit: 'extractedPagesPerMonth',
            used: 400,
            max: 400,
          },
          { status: 403, headers: { 'Content-Type': 'application/problem+json' } },
        ),
      ),
    )

    await expect(apiClient('/api/trigger-limit')).rejects.toThrow()
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText('You have reached a plan limit')).toBeInTheDocument()
  })
})
