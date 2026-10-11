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

let tokenProvider: TokenProvider | null = null
let unauthorizedHandler: UnauthorizedHandler | null = null

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

    throw new ProblemError(problem)
  }

  if (response.status === 204) {
    return {} as T
  }

  return (await response.json()) as T
}
