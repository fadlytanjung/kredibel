/**
 * SSE consumption for Finance Assistant (spec 011; AC-011-11).
 *
 * Handles Server-Sent Events over fetch for token streaming, live progress steps,
 * tool calls, and canonical message delivery.
 */

import type { AssistantMessage } from './api'
import { apiStream, ProblemError } from '../../shared/api/client'

export interface RawEvent {
  event: string
  data: string
}

export interface StepEvent {
  node: string
  label: string
}

export interface ToolEvent {
  name: string
  args_summary?: string
  ok: boolean
}

export interface StreamHandlers {
  onStep?: (step: StepEvent) => void
  onTool?: (tool: ToolEvent) => void
  onToken?: (text: string) => void
  onMessage?: (message: AssistantMessage) => void
  onError?: (error: { message: string; timeout?: boolean }) => void
  onDone?: () => void
}

/** CRLF and bare CR both mean "end of line" in SSE; only LF is kept internally. */
function normalise(text: string): string {
  return text.replace(/\r\n?/g, '\n')
}

function parseRecord(raw: string): RawEvent | null {
  let event = 'message'
  const data: string[] = []

  for (const line of raw.split('\n')) {
    if (!line || line.startsWith(':')) continue // blank or comment
    const separator = line.indexOf(':')
    const field = separator === -1 ? line : line.slice(0, separator)
    const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '')
    if (field === 'event') event = value
    else if (field === 'data') data.push(value)
  }

  return data.length ? { event, data: data.join('\n') } : null
}

/**
 * Parse an SSE byte stream into raw events.
 */
export async function* parseSSE(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<RawEvent> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let danglingCR = false

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break

      let text = decoder.decode(value, { stream: true })
      if (danglingCR) {
        text = `\r${text}`
        danglingCR = false
      }
      if (text.endsWith('\r')) {
        text = text.slice(0, -1)
        danglingCR = true
      }
      buffer += normalise(text)

      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const raw = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const parsed = parseRecord(raw)
        if (parsed) yield parsed
        boundary = buffer.indexOf('\n\n')
      }
    }
    if (danglingCR) buffer += '\n'
    const trailing = parseRecord(buffer)
    if (trailing) yield trailing
  } finally {
    reader.releaseLock()
  }
}

/**
 * Stream a question to the assistant using SSE.
 */
export async function streamQuestion(
  threadId: string,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await apiStream(`/api/assistant/threads/${threadId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (err) {
    if (signal?.aborted) return
    handlers.onError?.({
      message: err instanceof Error ? err.message : String(err),
      timeout: err instanceof ProblemError && err.code === 'GATEWAY_TIMEOUT',
    })
    handlers.onDone?.()
    return
  }

  if (!response.ok) {
    let errMsg = `Request failed: ${response.status}`
    try {
      const errBody = (await response.json()) as { detail?: string; message?: string }
      errMsg = errBody.detail || errBody.message || errMsg
    } catch {
      // ignore
    }
    handlers.onError?.({ message: errMsg })
    handlers.onDone?.()
    return
  }

  if (!response.body) {
    handlers.onError?.({ message: 'No response body stream available' })
    handlers.onDone?.()
    return
  }

  try {
    for await (const raw of parseSSE(response.body)) {
      if (raw.event === 'step') {
        try {
          const step = JSON.parse(raw.data) as StepEvent
          handlers.onStep?.(step)
        } catch {
          // ignore
        }
      } else if (raw.event === 'tool') {
        try {
          const tool = JSON.parse(raw.data) as ToolEvent
          handlers.onTool?.(tool)
        } catch {
          // ignore
        }
      } else if (raw.event === 'token') {
        try {
          const parsed = JSON.parse(raw.data) as { text: string }
          handlers.onToken?.(parsed.text)
        } catch {
          handlers.onToken?.(raw.data)
        }
      } else if (raw.event === 'message') {
        try {
          const msg = JSON.parse(raw.data) as AssistantMessage
          handlers.onMessage?.(msg)
        } catch {
          // ignore
        }
      } else if (raw.event === 'error') {
        try {
          const err = JSON.parse(raw.data) as { message: string }
          handlers.onError?.(err)
        } catch {
          handlers.onError?.({ message: raw.data })
        }
      } else if (raw.event === 'done') {
        handlers.onDone?.()
      }
    }
  } catch (err) {
    if (signal?.aborted) return
    handlers.onError?.({
      message: err instanceof Error ? err.message : String(err),
    })
    handlers.onDone?.()
  }
}
