import { describe, expect, it } from 'vitest'
import { shellPropsFromWorkspace, type Workspace } from './shellProps'

const workspace = (status: 'TRIALING' | 'TRIAL_EXPIRED', daysLeft: number): Workspace =>
  ({
    orgId: 'org_1',
    name: 'Synthetic Roasters Ltd',
    entityType: 'COMPANY',
    currency: 'IDR',
    timezone: 'Asia/Jakarta',
    profile: { accountingFramework: 'IFRS' },
    subscription: {
      planId: 'free_trial',
      status,
      trialDaysLeft: daysLeft,
      trialEndsAt: '2026-11-10T08:00:00+00:00',
      limits: { extractedPagesPerMonth: 400 },
    },
    usage: { extractedPages: 286 },
  }) as Workspace

describe('shellPropsFromWorkspace (AC-013-12)', () => {
  it('names the workspace and its trial', () => {
    const props = shellPropsFromWorkspace(workspace('TRIALING', 23))

    expect(props.workspace).toEqual({ name: 'Synthetic Roasters Ltd', subtitle: 'COMPANY · IDR · IFRS' })
    expect(props.trial).toEqual({ status: 'TRIALING', daysLeft: 23, pagesUsed: 286, pagesMax: 400 })
    expect(props.uploadBlocked).toBe(false)
  })

  it('blocks Upload after the trial', () => {
    expect(shellPropsFromWorkspace(workspace('TRIAL_EXPIRED', 0)).uploadBlocked).toBe(true)
  })
})
