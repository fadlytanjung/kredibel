import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, QueryProvider } from './app/providers'
import { PlanLimitProvider } from './features/plan-limit-dialog'
import { AppRouter } from './app/router'
import './shared/i18n/setup'

export function App() {
  return (
    <BrowserRouter>
      <QueryProvider>
        <AuthProvider>
          <PlanLimitProvider>
            <AppRouter />
          </PlanLimitProvider>
        </AuthProvider>
      </QueryProvider>
    </BrowserRouter>
  )
}

export default App
