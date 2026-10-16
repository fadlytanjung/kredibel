/**
 * Dev-only: the guided tour over the shell previews (spec 021, AC-021-4…6), for the Playwright
 * checks. Every page the tour opens is a preview under /preview/tour/; Playwright serves the API.
 * Not routed in production builds.
 */

import { Route, Routes } from 'react-router-dom'
import { TourProvider } from '../features/tour'
import {
  AssistantPreview,
  CounterpartiesPreview,
  DocumentsPreview,
  LabelsPreview,
  MonthsPreview,
  ReviewPreview,
  RiskPreview,
  RunsPreview,
  ShellPreview,
} from './ShellPreview'

export function TourPreview() {
  return (
    <TourProvider role="owner" uid="u_preview" workspaceName="Sunrise Coffee Roasters" pathFor={(path) => `/preview/tour${path}`}>
      <Routes>
        <Route path="dashboard" element={<ShellPreview />} />
        <Route path="documents" element={<DocumentsPreview />} />
        <Route path="months/all" element={<MonthsPreview />} />
        <Route path="review" element={<ReviewPreview />} />
        <Route path="risk" element={<RiskPreview />} />
        <Route path="counterparties" element={<CounterpartiesPreview />} />
        <Route path="labels" element={<LabelsPreview />} />
        <Route path="runs" element={<RunsPreview />} />
        <Route path="assistant" element={<AssistantPreview />} />
      </Routes>
    </TourProvider>
  )
}
