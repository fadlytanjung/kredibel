import { Navigate } from 'react-router-dom'
import { currentMonth } from '../shared/lib/formatDate'

/** Reconciliation is monthly: /months opens this calendar month (docs/11 §4.2). */
export function CurrentMonthRedirect() {
  return <Navigate to={`/months/${currentMonth()}`} replace />
}
