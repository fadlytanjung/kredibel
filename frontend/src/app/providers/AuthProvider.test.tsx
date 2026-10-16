import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useAuth } from '../../entities/session'
import { apiClient } from '../../shared/api/client'
import { AuthProvider } from './AuthProvider'

type Listener = (user: { uid: string; getIdToken: () => Promise<string> } | null) => Promise<void>
const firebase = vi.hoisted(() => ({ listener: null as Listener | null }))

vi.mock('firebase/auth', () => ({
  browserLocalPersistence: {},
  browserPopupRedirectResolver: {},
  onAuthStateChanged: (_auth: unknown, listener: Listener) => {
    firebase.listener = listener
    return () => undefined
  },
  setPersistence: vi.fn(),
  signInWithEmailAndPassword: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(async () => firebase.listener?.(null)),
}))
vi.mock('../../shared/firebase/app', () => ({ auth: { currentUser: null }, googleAuthProvider: {} }))
vi.mock('../../shared/api/client', () => ({
  apiClient: vi.fn(),
  setTokenProvider: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const me = (uid: string, orgId: string | null) => ({ uid, orgId, needsWorkspace: orgId === null })
const person = (uid: string) => ({ uid, getIdToken: async () => 'token' })

function setup() {
  const client = new QueryClient()
  const seen: { signOut?: () => Promise<void>; refreshMe?: () => Promise<void> } = {}
  function Probe() {
    const auth = useAuth()
    seen.signOut = auth.signOut
    seen.refreshMe = auth.refreshMe
    return null
  }
  render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  )
  return { client, seen }
}

describe('AuthProvider', () => {
  it('forgets the last account\'s cached workspace when another account signs in', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce(me('uid-a', 'org_a')).mockResolvedValueOnce(me('uid-b', null))
    const { client, seen } = setup()
    await act(async () => firebase.listener?.(person('uid-a')))
    client.setQueryData(['workspace'], { name: 'Workspace A' })

    await act(async () => seen.signOut?.())
    expect(client.getQueryData(['workspace'])).toBeUndefined()

    client.setQueryData(['workspace'], { name: 'Workspace A' })
    await act(async () => firebase.listener?.(person('uid-b')))
    await waitFor(() => expect(client.getQueryData(['workspace'])).toBeUndefined())
  })

  it('forgets cached data when the same person moves to another workspace', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce(me('uid-b', null)).mockResolvedValueOnce(me('uid-b', 'org_b'))
    const { client, seen } = setup()
    await act(async () => firebase.listener?.(person('uid-b')))
    client.setQueryData(['plans'], { plans: [] })
    client.setQueryData(['workspace'], { name: 'Workspace A' })

    await act(async () => seen.refreshMe?.())

    expect(client.getQueryData(['workspace'])).toBeUndefined()
  })
})
