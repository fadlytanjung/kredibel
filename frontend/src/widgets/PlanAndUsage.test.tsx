import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { PlanCatalog } from '../entities/plan'
import type { Workspace } from '../entities/workspace'
import { PlanAndUsage } from './PlanAndUsage'

const CATALOG: PlanCatalog = {
  plans: [
    {
      id: 'free_trial',
      label: 'Free trial',
      status: 'AVAILABLE',
      trialDays: 30,
      highlights: ['150 documents / mo', '400 pages / mo'],
      limits: {
        documentsPerMonth: 150,
        extractedPagesPerMonth: 400,
        aiSpendUsdPerMonth: '5.00',
        monthRunsPerDay: 5,
        seats: 3,
        assistantQuestionsPerDay: 50,
      },
    },
    {
      id: 'starter',
      label: 'Starter',
      status: 'COMING_SOON',
      priceLabel: 'IDR 290k / mo',
      highlights: ['500 documents / mo'],
    },
    {
      id: 'professional',
      label: 'Professional',
      status: 'COMING_SOON',
      priceLabel: 'IDR 890k / mo',
      highlights: ['2,000 documents / mo'],
    },
  ],
  comingSoonFeatures: [
    {
      id: 'loan_readiness_report',
      label: 'Loan readiness report',
      description: 'A bank-ready health pack export.',
    },
    {
      id: 'bank_feeds',
      label: 'Bank feeds',
      description: 'Automatic statement sync.',
    },
  ],
  languages: [{ code: 'en', label: 'English', status: 'available' }],
}

const WORKSPACE: Workspace = {
  orgId: 'org_1',
  name: 'Synthetic Roasters Ltd',
  entityType: 'COMPANY',
  country: 'ID',
  timezone: 'Asia/Jakarta',
  currency: 'IDR',
  defaultLanguage: 'en',
  subscription: {
    planId: 'free_trial',
    status: 'ACTIVE',
    trialEndsAt: '2026-11-02T00:00:00Z',
    trialDaysLeft: 23,
    limits: {
      documentsPerMonth: 150,
      extractedPagesPerMonth: 400,
      aiSpendUsdPerMonth: '5.00',
      monthRunsPerDay: 5,
      seats: 3,
      assistantQuestionsPerDay: 50,
    },
  },
  usage: {
    month: '2026-10',
    documentsUploaded: 30,
    extractedPages: 80,
    monthRunsToday: 1,
    assistantQuestionsToday: 5,
    aiSpendUsd: '0.42',
    seatsUsed: 1,
  },
  learning: { shareVerifiedLabels: false },
}

describe('PlanAndUsage (AC-013-11)', () => {
  it('renders trial status, usage meters, coming soon plans and features', () => {
    render(<PlanAndUsage workspace={WORKSPACE} catalog={CATALOG} />)

    // Trial hero
    expect(screen.getByText('23')).toBeInTheDocument()
    expect(screen.getByText(/days left/)).toBeInTheDocument()
    expect(screen.getByText(/Your free trial ends on/)).toBeInTheDocument()

    // Usage meters
    expect(screen.getByText('Documents this month')).toBeInTheDocument()
    expect(screen.getByText('30')).toBeInTheDocument()
    expect(screen.getByText('Pages read this month')).toBeInTheDocument()
    expect(screen.getByText('80')).toBeInTheDocument()

    // Plan cards
    expect(screen.getByText('Free trial')).toBeInTheDocument()
    expect(screen.getByText('Your plan')).toBeInTheDocument()
    expect(screen.getByText('Starter')).toBeInTheDocument()
    expect(screen.getByText('Professional')).toBeInTheDocument()

    const comingSoonBadges = screen.getAllByText('Coming soon')
    expect(comingSoonBadges.length).toBeGreaterThanOrEqual(4) // Starter, Professional, Loan readiness, Bank feeds

    // Buttons for coming-soon plans must be disabled (cannot start purchase)
    const disabledButtons = screen.getAllByRole('button', { name: 'Not available yet' })
    expect(disabledButtons.length).toBe(2)
    for (const btn of disabledButtons) {
      expect(btn).toBeDisabled()
    }

    // Coming-soon features
    expect(screen.getByText('Loan readiness report')).toBeInTheDocument()
    expect(screen.getByText('Bank feeds')).toBeInTheDocument()
  })

  it('warns when meters are near limit (>= 80%)', () => {
    const nearLimitWorkspace: Workspace = {
      ...WORKSPACE,
      usage: {
        ...WORKSPACE.usage!,
        documentsUploaded: 130, // 130 / 150 = 86%
        extractedPages: 350, // 350 / 400 = 87%
      },
    }

    render(<PlanAndUsage workspace={nearLimitWorkspace} catalog={CATALOG} />)

    const nearNotes = screen.getAllByText('Close to the limit.')
    expect(nearNotes.length).toBeGreaterThan(0)
  })

  it('renders expired trial state when TRIAL_EXPIRED', () => {
    const expiredWorkspace: Workspace = {
      ...WORKSPACE,
      subscription: {
        ...WORKSPACE.subscription,
        status: 'TRIAL_EXPIRED',
        trialDaysLeft: 0,
      },
    }

    render(<PlanAndUsage workspace={expiredWorkspace} catalog={CATALOG} />)

    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText(/Your free trial ended on/)).toBeInTheDocument()
  })
})
