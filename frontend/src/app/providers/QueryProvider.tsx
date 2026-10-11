import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

export function QueryProvider({ children }: { children: ReactNode }) {
  // One client per app instance; plan data changes rarely, so it stays fresh for minutes.
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 5 * 60_000, retry: 1 } },
      }),
  )
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
