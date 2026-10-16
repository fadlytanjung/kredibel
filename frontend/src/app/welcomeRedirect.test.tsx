/** Spec 024, AC-024-4: an owner whose workspace has no goal yet is asked it first (a new workspace,
 * a fresh demo copy); once a goal is recorded the pages open as before. Synthetic data only. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextType } from '../entities/session'
import { ProtectedRoute } from './router'

let goal: string | null = null
const server = setupServer(
  http.get('/api/workspace', () =>
    HttpResponse.json({ orgId: 'org_1', name: 'Synthetic Roasters', entityType: 'COMPANY', currency: 'IDR', timezone: 'Asia/Jakarta', goal, expectations: [], subscription: { planId: 'free_trial', status: 'TRIALING' } }),
  ),
  http.get('/api/review-items', () => HttpResponse.json({ items: [] })),
  http.get('/api/labels', () => HttpResponse.json({ items: [], summary: { needsCheck: 0 } })),
)
beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderAs(role: string) {
  const auth = {
    user: { email: 'owner@example.test' },
    me: { uid: 'u_1', orgId: 'org_1', role, needsWorkspace: false, tourSeen: true },
    loading: false,
    meError: false,
    needsWorkspace: false,
  } as unknown as AuthContextType
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route path="/dashboard" element={<ProtectedRoute><h1>Dashboard</h1></ProtectedRoute>} />
            <Route path="/welcome" element={<h1>Welcome question</h1>} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    </QueryClientProvider>,
  )
}

describe('the welcome question (AC-024-4)', () => {
  it('asks an owner whose workspace has no goal', async () => {
    goal = null
    renderAs('owner')
    expect(await screen.findByRole('heading', { name: 'Welcome question' })).toBeInTheDocument()
  })

  it('opens the page once a goal is recorded', async () => {
    goal = 'BOOKKEEPING'
    renderAs('owner')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('never asks a reviewer for the workspace goal', async () => {
    goal = null
    renderAs('reviewer')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Welcome question' })).toBeNull()
  })
})
