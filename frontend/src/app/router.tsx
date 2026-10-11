/**
 * Client router with authenticated and workspace-guarded routes.
 *
 * Normative references: docs/specs/001-foundation/spec.md AC-001-3, AC-001-4, and docs/11 §4.
 */

import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { OnboardingPage } from '../pages/OnboardingPage'
import {
  CounterpartiesPage,
  DocumentsPage,
  MonthsPage,
  ReviewPage,
  RiskPage,
  SettingsPage,
} from '../pages/Placeholders'
import { useAuth } from './providers/useAuth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, needsWorkspace, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-sm font-medium text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (needsWorkspace) {
    return <Navigate to="/onboarding" replace />
  }

  return <>{children}</>
}

export function OnboardingRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-sm font-medium text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/onboarding"
        element={
          <OnboardingRoute>
            <OnboardingPage />
          </OnboardingRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedRoute>
            <DocumentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/months"
        element={
          <ProtectedRoute>
            <MonthsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/review"
        element={
          <ProtectedRoute>
            <ReviewPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/risk"
        element={
          <ProtectedRoute>
            <RiskPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/counterparties"
        element={
          <ProtectedRoute>
            <CounterpartiesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
