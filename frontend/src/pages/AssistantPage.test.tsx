/**
 * Tests for AssistantPage (spec 011; AC-011-1, AC-011-2, AC-011-11; mock assistant.html).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient, apiStream } from '../shared/api/client'
import { AssistantPage } from './AssistantPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  apiStream: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

const MOCK_THREADS = {
  items: [
    {
      threadId: 'th_01',
      title: 'May Reconciliation Query',
      scope: '2026-05',
      createdAt: '2026-05-15T10:00:00Z',
      lastMessageAt: '2026-05-15T10:05:00Z',
    },
  ],
}

const MOCK_MESSAGES = {
  items: [
    {
      messageId: 'msg_01',
      role: 'user',
      question: 'Why is June risk scored as Medium?',
      createdAt: '2026-06-01T10:00:00Z',
    },
    {
      messageId: 'msg_02',
      role: 'assistant',
      createdAt: '2026-06-01T10:00:05Z',
      answer: {
        parts: [
          {
            type: 'text',
            text: 'June risk is Medium due to open finding [[finding:fnd_01]] regarding an unmatched transaction for 15,000,000 [[fact:2026-06:net]].',
          },
        ],
        citations: [
          { ref: 'finding:fnd_01', label: 'Finding fnd_01' },
          { ref: 'fact:2026-06:net', label: 'Fact Net June' },
        ],
        grounding: {
          verdict: 'AGREED',
          citations: ['finding:fnd_01', 'fact:2026-06:net'],
        },
        toolsUsed: ['get_period_summary', 'list_findings'],
      },
    },
  ],
}

const MOCK_MEMORIES = {
  items: [
    {
      memoryId: 'mem_01',
      fact: 'Show amounts in millions',
      updatedAt: '2026-06-01T10:00:00Z',
    },
    {
      memoryId: 'mem_02',
      fact: 'ACB ••5577 is the payroll account',
      updatedAt: '2026-06-01T10:00:00Z',
    },
  ],
}

function makeSSEStream(events: Array<{ event: string; data: string }>) {
  const encoder = new TextEncoder()
  const payload = events.map((e) => `event: ${e.event}\ndata: ${e.data}\n\n`).join('')
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(payload))
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

function renderWithClient(initialRoute = '/assistant/th_01') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/assistant/:threadId" element={<AssistantPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AssistantPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders threads and message conversation history with citations and grounding', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string) => {
      if (url.includes('/api/assistant/threads/th_01/messages')) {
        return MOCK_MESSAGES
      }
      if (url.includes('/api/assistant/threads')) {
        return MOCK_THREADS
      }
      if (url.includes('/api/assistant/memories')) {
        return MOCK_MEMORIES
      }
      return { items: [] }
    })

    renderWithClient('/assistant/th_01')

    await waitFor(() => {
      expect(screen.getByText('May Reconciliation Query')).toBeInTheDocument()
    })

    expect(screen.getByText('Why is June risk scored as Medium?')).toBeInTheDocument()
    expect(screen.getByText(/June risk is Medium due to open finding/)).toBeInTheDocument()
    expect(screen.getByText('fnd_01')).toBeInTheDocument()
    expect(screen.getByText('Every number checked against your books')).toBeInTheDocument()
    expect(screen.getByText('Remembered for you')).toBeInTheDocument()
    expect(screen.getByText('Show amounts in millions')).toBeInTheDocument()
  })

  it('renders suggested starter questions', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string) => {
      if (url.includes('/api/assistant/threads/th_empty/messages')) {
        return { items: [] }
      }
      if (url.includes('/api/assistant/threads')) {
        return {
          items: [
            {
              threadId: 'th_empty',
              title: 'Empty Conversation',
              scope: 'WORKSPACE',
              createdAt: '2026-06-01T10:00:00Z',
            },
          ],
        }
      }
      if (url.includes('/api/assistant/memories')) {
        return { items: [] }
      }
      return { items: [] }
    })

    renderWithClient('/assistant/th_empty')

    await waitFor(() => {
      expect(screen.getByTestId('assistant-welcome')).toBeInTheDocument()
      expect(screen.getAllByText('Which invoices are still unpaid?')[0]).toBeInTheDocument()
    })

    expect(screen.getByTestId('prompt-card-0')).toBeInTheDocument()
    expect(screen.getByLabelText('Suggested questions')).toBeInTheDocument()
    expect(screen.getAllByText('Where did the money go in Q2?')[0]).toBeInTheDocument()
  })

  it('allows user to stream a new question via composer with SSE', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string) => {
      if (url.includes('/api/assistant/threads/th_01/messages')) {
        return { items: [] }
      }
      if (url.includes('/api/assistant/threads')) {
        return MOCK_THREADS
      }
      if (url.includes('/api/assistant/memories')) {
        return { items: [] }
      }
      return { items: [] }
    })

    const streamResponse = makeSSEStream([
      { event: 'step', data: JSON.stringify({ node: 'plan', label: 'Planning query' }) },
      { event: 'tool', data: JSON.stringify({ name: 'get_period_summary', args_summary: '2026-05', ok: true }) },
      { event: 'token', data: JSON.stringify({ text: 'Current balance is IDR 50,000,000.' }) },
      {
        event: 'message',
        data: JSON.stringify({
          messageId: 'msg_streamed',
          role: 'assistant',
          createdAt: new Date().toISOString(),
          answer: {
            parts: [{ type: 'text', text: 'Current balance is IDR 50,000,000.' }],
            citations: [],
            grounding: { verdict: 'AGREED', citations: [] },
            toolsUsed: ['get_period_summary'],
          },
        }),
      },
      { event: 'done', data: '{}' },
    ])

    vi.mocked(apiStream).mockResolvedValue(streamResponse)

    renderWithClient('/assistant/th_01')

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Ask about your books')).toBeInTheDocument()
    })

    const input = screen.getByPlaceholderText('Ask about your books')
    fireEvent.change(input, { target: { value: 'What is our current balance?' } })

    const sendBtn = screen.getByRole('button', { name: /Send/i })
    fireEvent.click(sendBtn)

    await waitFor(() => {
      expect(apiStream).toHaveBeenCalledWith(
        '/api/assistant/threads/th_01/messages',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ question: 'What is our current balance?' }),
        }),
      )
    })

    expect(await screen.findByText('What is our current balance?')).toBeInTheDocument()
    expect(await screen.findByText(/Current balance is IDR 50,000,000/)).toBeInTheDocument()
  })

  it('allows user to forget remembered preferences', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string, opts?: RequestInit) => {
      if (opts?.method === 'DELETE') {
        return undefined
      }
      if (url.includes('/messages')) {
        return { items: [] }
      }
      if (url.includes('/api/assistant/threads')) {
        return MOCK_THREADS
      }
      if (url.includes('/api/assistant/memories')) {
        return MOCK_MEMORIES
      }
      return { items: [] }
    })

    renderWithClient('/assistant/th_01')

    await waitFor(() => {
      expect(screen.getByText('Forget all')).toBeInTheDocument()
    })

    const forgetAllBtn = screen.getByText('Forget all')
    fireEvent.click(forgetAllBtn)

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith('/api/assistant/memories', { method: 'DELETE' })
    })
  })

  it('allows user to paginate earlier questions history', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string) => {
      if (url.includes('/messages')) {
        return { items: [] }
      }
      if (url.includes('/api/assistant/threads') && url.includes('cursor=th_01')) {
        return {
          items: [
            {
              threadId: 'th_02',
              title: 'April Reconciliation',
              scope: '2026-04',
              createdAt: '2026-04-15T10:00:00Z',
            },
          ],
          nextCursor: null,
        }
      }
      if (url.includes('/api/assistant/threads')) {
        return {
          items: [
            {
              threadId: 'th_01',
              title: 'May Reconciliation Query',
              scope: '2026-05',
              createdAt: '2026-05-15T10:00:00Z',
            },
          ],
          nextCursor: 'th_01',
        }
      }
      if (url.includes('/api/assistant/memories')) {
        return { items: [] }
      }
      return { items: [] }
    })

    renderWithClient('/assistant/th_01')

    await waitFor(() => {
      expect(screen.getByText('May Reconciliation Query')).toBeInTheDocument()
    })

    const loadMoreBtn = screen.getByRole('button', { name: /Load earlier questions/i })
    expect(loadMoreBtn).toBeInTheDocument()
    fireEvent.click(loadMoreBtn)

    await waitFor(() => {
      expect(screen.getByText('April Reconciliation')).toBeInTheDocument()
    })
  })
})
