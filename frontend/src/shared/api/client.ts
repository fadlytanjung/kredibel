/**
 * Typed API client with RFC 9457 problem details parsing and 401 unauthenticated handling.
 *
 * Normative reference: docs/specs/001-foundation/spec.md AC-001-5 and docs/11 §3.
 */

export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail?: string
  code?: string
  [key: string]: unknown
}

export class ProblemError extends Error {
  readonly status: number
  readonly code: string
  readonly problem: ProblemDetails

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title || `HTTP error ${problem.status}`)
    this.name = 'ProblemError'
    this.status = problem.status
    this.code = problem.code || 'UNKNOWN_ERROR'
    this.problem = problem
  }
}

type TokenProvider = () => Promise<string | null> | string | null
type UnauthorizedHandler = () => void
type ProblemListener = (problem: ProblemError) => void

let tokenProvider: TokenProvider | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null
let problemListener: ProblemListener | null = null

/** Hears every problem response, e.g. to open the PlanLimitDialog wherever a limit is hit
 *  (docs/11 §5.4, §7a). The caller still receives the error. */
export function setProblemListener(listener: ProblemListener | null): void {
  problemListener = listener
}

export function setTokenProvider(provider: TokenProvider | null): void {
  tokenProvider = provider
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler
}

export async function apiClient<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await authedFetch(path, options)
  if (response.status === 204) {
    return {} as T
  }
  return (await response.json()) as T
}

/**
 * Binary responses (page images, the original file) with the same token and problem handling.
 * An `<img src>` or a plain link cannot send the token, so the SPA fetches these and shows them
 * from an object URL (docs/11 §6.3).
 */
export async function apiBlob(path: string, options: RequestInit = {}): Promise<Blob> {
  const headers = new Headers(options.headers || {})
  if (!headers.has('Accept')) headers.set('Accept', '*/*, application/problem+json')
  const response = await authedFetch(path, { ...options, headers })
  return response.blob()
}

async function authedFetch(path: string, options: RequestInit): Promise<Response> {
  const headers = new Headers(options.headers || {})

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json, application/problem+json')
  }

  if (!headers.has('Authorization') && tokenProvider) {
    const token = await tokenProvider()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  const response = await fetch(path, {
    ...options,
    headers,
  })

  if (!response.ok) {
    if (response.status === 401 && unauthorizedHandler) {
      unauthorizedHandler()
    }

    let problem: ProblemDetails
    const contentType = response.headers.get('content-type') || ''

    if (contentType.includes('json')) {
      try {
        problem = (await response.json()) as ProblemDetails
      } catch {
        problem = {
          type: 'about:blank',
          title: response.statusText || 'HTTP Error',
          status: response.status,
          code: 'HTTP_ERROR',
        }
      }
    } else {
      const text = await response.text()
      problem = {
        type: 'about:blank',
        title: response.statusText || 'HTTP Error',
        status: response.status,
        detail: text,
        code: 'HTTP_ERROR',
      }
    }

    const error = new ProblemError(problem)
    problemListener?.(error)
    throw error
  }

  return response
}
