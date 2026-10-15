/**
 * The synthetic dashboard shared with the HTML mock (contracts/design/fixtures/dashboard.json,
 * AC-019-2): Sunrise Coffee Roasters, January to June 2026. Browser tests serve it as /api/dashboard.
 */
import type { Dashboard } from '../../entities/insight'
import dashboard from '../../../../contracts/design/fixtures/dashboard.json' with { type: 'json' }

export const DASHBOARD = dashboard as Dashboard

/** The workspace the mocks' shell shows (tools/design/mocks/shell.py). */
export const WORKSPACE = {
  orgId: 'org_synthetic',
  name: 'Sunrise Coffee Roasters',
  currency: 'IDR',
  kind: 'COMPANY',
  profile: { accountingFramework: 'IFRS' },
}
