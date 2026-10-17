import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextType } from '../entities/session'
import type { BankAccount } from '../entities/bank-account'
import type { PlanCatalog } from '../entities/plan'
import type { Workspace } from '../entities/workspace'
import { SettingsPage } from './SettingsPage'

const CATALOG: PlanCatalog = {
  plans: [
    {
      id: 'free_trial',
      label: 'Free trial',
      status: 'AVAILABLE',
      trialDays: 30,
      highlights: ['150 documents / mo', '400 pages / mo'],
      limits: {
        documentsPerMonth: 150,
        extractedPagesPerMonth: 400,
        aiSpendUsdPerMonth: '5.00',
        monthRunsPerDay: 5,
        seats: 3,
        assistantQuestionsPerDay: 50,
      },
    },
    {
      id: 'starter',
      label: 'Starter',
      status: 'COMING_SOON',
      priceLabel: 'IDR 290k / mo',
      highlights: [],
    },
  ],
  comingSoonFeatures: [],
  languages: [
    { code: 'en', label: 'English', status: 'available' },
    { code: 'id', label: 'Indonesian', status: 'coming_soon' },
  ],
}

let mockWorkspace: Workspace = {
  orgId: 'org_1',
  name: 'Synthetic Roasters Ltd',
  entityType: 'COMPANY',
  country: 'ID',
  timezone: 'Asia/Jakarta',
  currency: 'IDR',
  defaultLanguage: 'en',
  profile: {
    legalName: 'Synthetic Roasters Ltd',
    tradingName: 'Synthetic Roasters',
    legalForm: 'LIMITED_COMPANY',
    industry: 'Food and drink, wholesale',
    taxIdMasked: '•••• 1234',
    address: { line1: 'Jl. Sudirman 1', city: 'Jakarta' },
    aliases: ['SR Ltd', 'Synth Roasters'],
  },
  subscription: {
    planId: 'free_trial',
    status: 'ACTIVE',
    trialEndsAt: '2026-11-02T00:00:00Z',
    trialDaysLeft: 23,
    limits: {
      documentsPerMonth: 150,
      extractedPagesPerMonth: 400,
      aiSpendUsdPerMonth: '5.00',
      monthRunsPerDay: 5,
      seats: 3,
      assistantQuestionsPerDay: 50,
    },
  },
  usage: {
    month: '2026-10',
    documentsUploaded: 10,
    extractedPages: 25,
    monthRunsToday: 1,
    assistantQuestionsToday: 0,
    aiSpendUsd: '0.10',
    seatsUsed: 1,
  },
  learning: { shareVerifiedLabels: false },
}

let mockAccounts: BankAccount[] = [
  {
    accountId: 'acc_1',
    bankName: 'Bank Sintetis',
    accountMasked: '•••• •••• •••• 4821',
    holderName: 'Synthetic Roasters Ltd',
    nickname: 'Main Operating',
    source: 'DECLARED',
    ledgerAccountCode: '1010',
  },
]

let lastPatchWorkspace: unknown = null
let lastAddedAccount: unknown = null
let lastPatchedAccount: { id: string; body: unknown } | null = null
let lastDeletedAccountId: string | null = null

const server = setupServer(
  http.get('/api/workspace', () => HttpResponse.json(mockWorkspace)),
  http.patch('/api/workspace', async ({ request }) => {
    lastPatchWorkspace = await request.json()
    const patch = lastPatchWorkspace as Partial<Workspace>
    mockWorkspace = {
      ...mockWorkspace,
      name: patch.name ?? mockWorkspace.name,
      profile: { ...mockWorkspace.profile, ...(patch.profile ?? {}) },
    }
    return HttpResponse.json(mockWorkspace)
  }),
  http.get('/api/plans', () => HttpResponse.json(CATALOG)),
  http.get('/api/suggestions', () => HttpResponse.json({ items: [] })),
  http.get('/api/bank-accounts', () => HttpResponse.json({ items: mockAccounts })),
  http.post('/api/bank-accounts', async ({ request }) => {
    lastAddedAccount = await request.json()
    const body = lastAddedAccount as { bankName: string; accountNumber: string; holderName: string }
    const newAcc: BankAccount = {
      accountId: 'acc_new',
      bankName: body.bankName,
      accountMasked: '•••• ' + body.accountNumber.slice(-4),
      holderName: body.holderName,
      source: 'DECLARED',
    }
    mockAccounts.push(newAcc)
    return HttpResponse.json(newAcc, { status: 201 })
  }),
  http.patch('/api/bank-accounts/:id', async ({ params, request }) => {
    lastPatchedAccount = { id: params.id as string, body: await request.json() }
    const patch = lastPatchedAccount.body as Partial<BankAccount>
    mockAccounts = mockAccounts.map((a) => (a.accountId === params.id ? { ...a, ...patch } : a))
    return HttpResponse.json(mockAccounts.find((a) => a.accountId === params.id))
  }),
  http.delete('/api/bank-accounts/:id', ({ params }) => {
    lastDeletedAccountId = params.id as string
    mockAccounts = mockAccounts.filter((a) => a.accountId !== params.id)
    return new HttpResponse(null, { status: 204 })
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  lastPatchWorkspace = null
  lastAddedAccount = null
  lastPatchedAccount = null
  lastDeletedAccountId = null
})
afterAll(() => server.close())

function renderSettings(initialSection = 'plan') {
  const auth = {
    user: { email: 'owner@example.test' },
    signOut: vi.fn(),
  } as unknown as AuthContextType

  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[`/settings/${initialSection}`]}>
          <Routes>
            <Route path="/settings/:section" element={<SettingsPage />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
  return { user: userEvent.setup(), auth }
}

describe('SettingsPage (AC-013-14…16)', () => {
  it('renders the section subnav with Team as coming soon', async () => {
    renderSettings('plan')

    expect(await screen.findByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Plan and usage' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Profile' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Bank accounts' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Language and formats' })).toBeInTheDocument()

    // Team (soon) is disabled in the subnav (P1 roles)
    const team = screen.getByRole('link', { name: 'Team (soon)' })
    expect(team).toHaveAttribute('aria-disabled', 'true')
  })

  it('renders Profile form, shows fixed type and masked tax ID, and saves changes (AC-013-14)', async () => {
    const { user } = renderSettings('profile')

    expect(await screen.findByDisplayValue('Synthetic Roasters Ltd')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Synthetic Roasters')).toBeInTheDocument()
    expect(screen.getByText('A company')).toBeInTheDocument() // Entity type label
    expect(screen.getByText(/Stored as •••• 1234/)).toBeInTheDocument() // Masked tax ID

    const nameInput = screen.getByLabelText('Legal name')
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Roasters Corp')

    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText('Saved.')).toBeInTheDocument()
    expect(lastPatchWorkspace).toMatchObject({
      name: 'Updated Roasters Corp',
      profile: expect.objectContaining({
        legalName: 'Updated Roasters Corp',
      }),
    })
  })

  it('manages bank accounts: list, add, edit nickname and remove (AC-013-14)', async () => {
    const { user } = renderSettings('bank-accounts')

    // Listed account with mask and nickname
    expect(await screen.findByText('Main Operating')).toBeInTheDocument()
    expect(screen.getByText(/•••• •••• •••• 4821/)).toBeInTheDocument()

    // Add account
    await user.click(screen.getByRole('button', { name: 'Add a bank account' }))
    await user.type(screen.getByLabelText('Bank'), 'BCA')
    await user.type(screen.getByLabelText('Account number'), '888-001-2345')
    await user.type(screen.getByLabelText('Account holder'), 'Synthetic Roasters Ltd')
    await user.click(screen.getByRole('button', { name: 'Add a bank account' }))

    await waitFor(() => expect(lastAddedAccount).toBeTruthy())
    expect(lastAddedAccount).toMatchObject({
      bankName: 'BCA',
      accountNumber: '888-001-2345',
      holderName: 'Synthetic Roasters Ltd',
    })

    // Edit nickname
    const [firstEditBtn] = screen.getAllByRole('button', { name: 'Edit' })
    await user.click(firstEditBtn)
    const nicknameInput = screen.getByDisplayValue('Main Operating')
    await user.clear(nicknameInput)
    await user.type(nicknameInput, 'Primary Payroll')
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(lastPatchedAccount).toBeTruthy())
    expect(lastPatchedAccount?.body).toMatchObject({
      nickname: 'Primary Payroll',
    })

    // Delete account
    const [firstRemoveBtn] = screen.getAllByRole('button', { name: 'Remove' })
    await user.click(firstRemoveBtn)
    expect(screen.getByText('Remove •••• •••• •••• 4821?')).toBeInTheDocument()
    const [confirmRemoveBtn] = screen.getAllByRole('button', { name: 'Remove' })
    await user.click(confirmRemoveBtn)

    await waitFor(() => expect(lastDeletedAccountId).toBe('acc_1'))
  })

  it('renders Language & formats with English selected, the currency fixed and the date format read-only (AC-013-15)', async () => {
    renderSettings('language')

    expect(await screen.findByText('English')).toBeInTheDocument()
    const englishRadio = screen.getByRole('radio', { name: /English/ })
    expect(englishRadio).toBeChecked()

    // Coming soon language disabled
    const indonesianRadio = screen.getByRole('radio', { name: /Indonesian/ })
    expect(indonesianRadio).toBeDisabled()

    // The currency is fixed after onboarding; changing it is coming soon (ADR-020)
    expect(screen.getByText(/\(IDR\)/)).toBeInTheDocument()
    expect(
      screen.getByText('Chosen when the workspace was created. Changing the currency is coming soon.'),
    ).toBeInTheDocument()
    expect(screen.getAllByText('Set by your workspace; it cannot change yet.')).toHaveLength(1)
  })
})
