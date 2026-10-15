import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import counterparties from '../../../../contracts/design/fixtures/counterparties.json' with { type: 'json' }
import { apiClient } from '../../shared/api/client'
import { SuggestionCard } from './SuggestionCard'

vi.mock('../../shared/api/client', () => ({ apiClient: vi.fn(), ProblemError: class ProblemError extends Error {} }))

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <SuggestionCard />
    </QueryClientProvider>,
  )
}

describe('SuggestionCard (spec 014, AC-014-7)', () => {
  beforeEach(() => {
    vi.mocked(apiClient).mockReset()
  })

  it('says what was found, with its confidence and evidence, and lets a person decide', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.startsWith('/api/suggestions?status=PENDING')) return { items: counterparties.suggestions }
      if (init?.method === 'PATCH') return { ...counterparties.suggestions[0], status: 'ACCEPTED' }
      throw new Error(`unexpected ${url}`)
    })
    mount()
    expect(await screen.findByText('Kredibel found 2 details for your profile')).toBeInTheDocument()
    expect(screen.getByText('Tax ID: ••••.000')).toBeInTheDocument()
    expect(screen.getByText(/High confidence, From 2 documents/)).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Accept' })[0])
    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        '/api/suggestions/sug_0f1e2d3c4b5a6978',
        expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ decision: 'ACCEPT' }) }),
      ),
    )
  })

  it('renders nothing when nothing is open', async () => {
    vi.mocked(apiClient).mockResolvedValue({ items: [] })
    const { container } = mount()
    await waitFor(() => expect(apiClient).toHaveBeenCalled())
    expect(container.querySelector('section')).toBeNull()
  })
})
