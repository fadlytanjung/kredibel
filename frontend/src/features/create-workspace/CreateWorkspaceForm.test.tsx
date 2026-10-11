import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthContext, type AuthContextType, type MeResponse } from '../../entities/session'
import { setTokenProvider } from '../../shared/api/client'
import { CreateWorkspaceForm } from './CreateWorkspaceForm'

const PLANS = {
  plans: [
    {
      id: 'free_trial',
      label: 'Free trial',
      status: 'AVAILABLE',
      trialDays: 30,
      highlights: [],
      limits: { documentsPerMonth: 150, extractedPagesPerMonth: 400 },
    },
    { id: 'starter', label: 'Starter', status: 'COMING_SOON', highlights: [] },
  ],
  comingSoonFeatures: [],
  languages: [{ code: 'en', label: 'English', status: 'available' }],
}

interface CreateResult {
  status: number
  body: object
}
const CREATED: CreateResult = { status: 201, body: { orgId: 'org_1' } }
const problem = (status: number, code: string, extra: object = {}): CreateResult => ({
  status,
  body: { type: 'about:blank', title: code, status, code, ...extra },
})

let created: unknown[] = []
let createResult = CREATED

const server = setupServer(
  http.get('/api/plans', () => HttpResponse.json(PLANS)),
  http.post('/api/workspaces', async ({ request }) => {
    created.push(await request.json())
    const contentType = createResult.status >= 400 ? 'application/problem+json' : 'application/json'
    return HttpResponse.json(createResult.body, {
      status: createResult.status,
      headers: { 'Content-Type': contentType },
    })
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  created = []
  createResult = CREATED
  setTokenProvider(null)
})
afterAll(() => server.close())

const me = (needsWorkspace: boolean) =>
  ({ uid: 'u-1', orgId: needsWorkspace ? null : 'org_1', needsWorkspace }) as MeResponse

function renderForm(refreshes: MeResponse[] = [me(false)]) {
  const refreshSession = vi.fn(async () => refreshes.shift() ?? me(false))
  const auth = {
    user: { email: 'owner@example.test' },
    refreshSession,
    signOut: vi.fn(),
  } as unknown as AuthContextType
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/onboarding']}>
          <Routes>
            <Route path="/onboarding" element={<CreateWorkspaceForm retryDelayMs={5} />} />
            <Route path="/" element={<p>Dashboard home</p>} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
  return { refreshSession, user: userEvent.setup(), auth }
}

describe('CreateWorkspaceForm (AC-013-2)', () => {
  it('switches the name field between a company and a person', async () => {
    const { user } = renderForm()

    expect(screen.getByLabelText('Legal name')).toBeInTheDocument()
    await user.click(screen.getByRole('radio', { name: /Myself/ }))
    expect(screen.getByLabelText('Full name')).toBeInTheDocument()
  })

  it('states the trial terms from the plan catalog before the button', async () => {
    renderForm()

    expect(await screen.findByText(/30-day free trial/)).toBeInTheDocument()
    expect(screen.getByText(/150 documents and 400 pages a month/)).toBeInTheDocument()
  })

  it('creates the workspace, refreshes the session and lands on the dashboard', async () => {
    const { user, refreshSession } = renderForm()

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.selectOptions(screen.getByLabelText('Industry'), 'Professional services')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByText('Dashboard home')).toBeInTheDocument()
    expect(created).toEqual([
      expect.objectContaining({
        name: 'Synthetic Roasters Ltd',
        entityType: 'COMPANY',
        country: 'ID',
        profile: { industry: 'Professional services' },
      }),
    ])
    expect(refreshSession).toHaveBeenCalledOnce()
  })

  it('checks the bank account before sending it', async () => {
    const { user } = renderForm()

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    const details = screen.getByText('Main bank account').closest('details')!
    details.open = true
    fireEvent(details, new Event('toggle'))
    await user.type(screen.getByLabelText('Bank'), 'Bank Sintetis')
    await user.type(screen.getByLabelText('Account number'), '12ab')
    await user.type(screen.getByLabelText('Account holder'), 'SR Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByText(/Use 6 to 30 digits/)).toBeInTheDocument()
    expect(created).toEqual([])

    await user.clear(screen.getByLabelText('Account number'))
    await user.type(screen.getByLabelText('Account number'), '123-456-4821')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    await screen.findByText('Dashboard home')
    expect(created[0]).toMatchObject({
      bankAccounts: [{ bankName: 'Bank Sintetis', accountNumber: '123-456-4821', holderName: 'SR Ltd' }],
    })
  })

  it('waits and retries once when the new token has no workspace yet', async () => {
    const { user, refreshSession } = renderForm([me(true), me(false)])

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByText('Dashboard home')).toBeInTheDocument()
    expect(refreshSession).toHaveBeenCalledTimes(2)
  })

  it('says so when the session still has no workspace after the retry', async () => {
    const { user } = renderForm([me(true), me(true)])

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByText(/this session has not caught up yet/)).toBeInTheDocument()
  })

  it('treats ALREADY_IN_WORKSPACE as created and refreshes (AC-013-3)', async () => {
    createResult = problem(409, 'ALREADY_IN_WORKSPACE')
    const { user } = renderForm()

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByText('Dashboard home')).toBeInTheDocument()
  })

  it('shows SIGNUP_CLOSED in words (AC-013-3)', async () => {
    createResult = problem(403, 'SIGNUP_CLOSED')
    const { user, refreshSession } = renderForm()

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'New workspaces cannot be created right now.',
    )
    expect(refreshSession).not.toHaveBeenCalled()
  })

  it('puts the server field errors on the fields', async () => {
    createResult = problem(422, 'VALIDATION_ERROR', {
      errors: [{ field: 'timezone', message: 'Unknown time zone' }],
    })
    const { user } = renderForm()

    await user.type(screen.getByLabelText('Legal name'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Start the free trial' }))

    await waitFor(() => expect(screen.getByText('Unknown time zone')).toBeInTheDocument())
    expect(screen.getByLabelText('Time zone')).toHaveAttribute('aria-invalid', 'true')
  })
})

describe('CreateWorkspaceForm footer', () => {
  it('offers sign-out as the signed-in user', async () => {
    const { user, auth } = renderForm()

    expect(screen.getByText(/Signed in as owner@example\.test\./)).toBeInTheDocument()
    const signOutBtn = screen.getByRole('button', { name: 'Sign out' })
    expect(signOutBtn).toBeInTheDocument()
    await user.click(signOutBtn)
    expect(auth.signOut).toHaveBeenCalled()
  })
})
