/**
 * The guided tour (spec 021, AC-021-4, AC-021-5): started by `?tour=1` after a workspace is
 * created, or by Take the tour; each step opens its page, then the overlay lights its part. Once
 * ended (Skip, Esc or Done) it is remembered for this person in this browser.
 */

import { useQuery } from '@tanstack/react-query'
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { apiClient } from '../../shared/api/client'
import { booksPeriod, stepPath, tourSteps } from './steps'
import { TourOverlay } from './TourOverlay'

interface TourContextValue {
  start: () => void
  active: boolean
}

const TourContext = createContext<TourContextValue>({ start: () => undefined, active: false })

// eslint-disable-next-line react-refresh/only-export-components -- the hook belongs with its provider
export const useTour = () => useContext(TourContext)

const seenKey = (uid: string) => `kredibel.tour.seen.${uid}`

function seen(uid: string | undefined): boolean {
  try {
    return Boolean(uid && window.localStorage.getItem(seenKey(uid)))
  } catch {
    return false
  }
}

function remember(uid: string | undefined) {
  try {
    if (uid) window.localStorage.setItem(seenKey(uid), '1')
  } catch {
    // Private windows may refuse storage; the tour simply may show again.
  }
}

export function TourProvider({
  children,
  role,
  uid,
  workspaceName,
  autoStart = false,
  onSeen,
  pathFor = (path) => path,
}: {
  children: ReactNode
  role?: string | null
  uid?: string
  workspaceName?: string
  /** The person has not seen the tour yet (`tourSeen` on /api/me): it starts by itself, once. */
  autoStart?: boolean
  /** Records on the server that the tour was finished or skipped. */
  onSeen?: () => void
  /** Previews map the app's paths to their own. */
  pathFor?: (path: string) => string
}) {
  const navigate = useNavigate()
  const location = useLocation()
  const steps = useMemo(() => tourSteps(role), [role])
  const [index, setIndex] = useState<number | null>(null)
  const active = index !== null
  // The months that have books, so the dashboard steps show them (AC-021-5).
  const { data: books } = useQuery({
    queryKey: ['tour-books'],
    queryFn: () => apiClient<{ months: { month: string }[] }>('/api/dashboard?period=all'),
    enabled: active,
    staleTime: 60_000,
  })
  const period = booksPeriod((books?.months ?? []).map((m) => m.month))

  const start = useCallback(() => setIndex(0), [])
  const stop = useCallback(() => {
    setIndex(null)
    remember(uid)
    onSeen?.()
  }, [uid, onSeen])

  // After onboarding the dashboard opens with ?tour=1: the tour starts (state derived while
  // rendering, as React allows), and the flag leaves the address.
  const asked = new URLSearchParams(location.search).get('tour') === '1'
  // A fresh person (the server says the tour is not seen) gets it once, wherever they land first.
  const [handled, setHandled] = useState(false)
  if ((asked || autoStart) && !handled) {
    setHandled(true)
    if (index === null && !seen(uid)) setIndex(0)
  }
  useEffect(() => {
    if (!asked) return
    const params = new URLSearchParams(location.search)
    params.delete('tour')
    navigate({ pathname: location.pathname, search: params.toString() }, { replace: true })
  }, [asked, location.pathname, location.search, navigate])

  const step = index !== null ? steps[index] : null
  const target = step ? pathFor(stepPath(step, period)) : null
  useEffect(() => {
    if (!target) return
    const [pathname, search = ''] = target.split('?')
    const here = location.pathname === pathname && (search === '' || location.search === `?${search}`)
    if (!here) navigate(target)
  }, [target, location.pathname, location.search, navigate])

  const value = useMemo(() => ({ start, active }), [start, active])
  return (
    <TourContext.Provider value={value}>
      {children}
      {step && index !== null && (
        <TourOverlay
          key={step.id}
          step={step}
          index={index}
          total={steps.length}
          workspaceName={workspaceName}
          onBack={() => setIndex(Math.max(index - 1, 0))}
          onNext={() => (index + 1 >= steps.length ? stop() : setIndex(index + 1))}
          onStop={stop}
        />
      )}
    </TourContext.Provider>
  )
}
