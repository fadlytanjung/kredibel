import { BrowserRouter } from 'react-router-dom'
import { AuthProvider, QueryProvider } from './app/providers'
import { AppRouter } from './app/router'
import './shared/i18n/setup'

export function App() {
  return (
    <BrowserRouter>
      <QueryProvider>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </QueryProvider>
    </BrowserRouter>
  )
}

export default App
