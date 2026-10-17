import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { apiClient, ProblemError, setUnauthorizedHandler } from './client'

const server = setupServer(
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'ok', version: 'dev', role: 'all' })
  }),
  http.get('/api/protected', () => {
    return new HttpResponse(
      JSON.stringify({
        type: 'about:blank',
        title: 'Unauthorized',
        status: 401,
        detail: 'Missing or malformed Authorization header',
        code: 'UNAUTHENTICATED',
      }),
      {
        status: 401,
        headers: { 'Content-Type': 'application/problem+json' },
      },
    )
  }),
  http.get('/api/workspace-data', () => {
    return new HttpResponse(
      JSON.stringify({
        type: 'about:blank',
        title: 'Workspace required',
        status: 403,
        detail: 'A workspace claim is required',
        code: 'WORKSPACE_REQUIRED',
      }),
      {
        status: 403,
        headers: { 'Content-Type': 'application/problem+json' },
      },
    )
  }),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  vi.restoreAllMocks()
})
afterAll(() => server.close())

describe('apiClient', () => {
  it('successfully fetches and parses JSON data', async () => {
    const data = await apiClient<{ status: string }>('/api/health')
    expect(data.status).toBe('ok')
  })

  it('parses RFC 9457 problem JSON and throws ProblemError', async () => {
    try {
      await apiClient('/api/workspace-data')
      expect.fail('Should have thrown ProblemError')
    } catch (err) {
      expect(err).toBeInstanceOf(ProblemError)
      const problemErr = err as ProblemError
      expect(problemErr.status).toBe(403)
      expect(problemErr.code).toBe('WORKSPACE_REQUIRED')
      expect(problemErr.problem.title).toBe('Workspace required')
    }
  })

  it('turns a gateway\'s HTML page (Firebase Hosting after 60 s) into a timeout, not a message', async () => {
    server.use(
      http.get('/api/slow', () =>
        new HttpResponse('<!DOCTYPE html><html><body>504 Gateway Timeout</body></html>', {
          status: 504,
          statusText: 'Gateway Timeout',
          headers: { 'content-type': 'text/html' },
        }),
      ),
    )
    try {
      await apiClient('/api/slow')
      expect.fail('Should have thrown ProblemError')
    } catch (err) {
      const problemErr = err as ProblemError
      expect(problemErr.code).toBe('GATEWAY_TIMEOUT')
      expect(problemErr.message).toBe('Gateway Timeout')
      expect(problemErr.message).not.toContain('<')
    }
  })

  it('triggers unauthorized handler on 401 response', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    try {
      await apiClient('/api/protected')
      expect.fail('Should have thrown ProblemError on 401')
    } catch (err) {
      expect(err).toBeInstanceOf(ProblemError)
      expect((err as ProblemError).status).toBe(401)
      expect(onUnauthorized).toHaveBeenCalledTimes(1)
    }
  })
})
