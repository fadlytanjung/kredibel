/**
 * Runs page parity with its mock (spec 017, AC-017-5…7; spec 019 AC-019-4): the same synthetic
 * fixture as design/mocks/runs.html, three widths, 360/1600 bounds, axe. The chips, the table,
 * the selected run's waterfall and the inspector are compared.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, RUNS, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)
const SELECTED = RUNS.items[0].runId

async function serve(page: Page, role = 'owner') {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    const events = path.match(/^\/api\/runs\/([\w-]+)\/events$/)
    const one = path.match(/^\/api\/runs\/([\w-]+)$/)
    if (path === '/api/me') return route.fulfill({ json: { uid: 'u_maya', orgId: 'org_synthetic', role, needsWorkspace: false, displayName: 'Maya Sari' } })
    if (path === '/api/runs') return route.fulfill({ json: { items: RUNS.items, nextCursor: null } })
    if (events) return route.fulfill({ json: (RUNS.events as Record<string, unknown>)[events[1]] ?? { items: [], contentCaptured: false } })
    if (one) return route.fulfill({ json: RUNS.items.find((r) => r.runId === one[1]) })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    return route.fulfill({ json: { items: [] } })
  })
}

async function axeClean(page: Page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
}

async function noOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
}

/** The page as a person sees it: chips, the runs, the selected run's spans and the inspector. */
async function outline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2):visible'),
    chips: await texts(page, '#content .chips .chip'),
    columns: await texts(page, '#content .runs-table th:visible'),
    runs: await texts(page, '#content .runs-table tbody strong'),
    statuses: await texts(page, '#content .runs-table .status-line'),
    durations: await texts(page, '#content .runs-table td.r:nth-child(4)'),
    models: await texts(page, '#content .runs-table td.small:visible'),
    summary: await texts(page, '#content .run-detail > .spread p'),
    spans: await texts(page, '#content .span-row .span-name'),
    spanDurations: await texts(page, '#content .span-row .span-dur'),
    spanDetails: await texts(page, '#content .span-row .span-detail'),
    inspector: await texts(page, '#content .ev-inspector h2, #content .ev-inspector dd, #content .ev-inspector .button, #content .ev-inspector .lp-side p'),
  }
}

test('AC-017-5: the owner sees every run with its calls, tokens, cost and labels like the mock', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/runs/${SELECTED}`)
  await expect(page.getByRole('heading', { name: 'Runs' })).toBeVisible()
  await expect(page.getByRole('heading', { name: /document_workflow on ACB_Mar_2026.pdf/ })).toBeVisible()
  await noOverflow(page)
  await expect(page).toHaveScreenshot('runs.png', { fullPage: true })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('runs'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-017-6: selecting a span shows its call; the trace link and the label are one click away', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/runs/${SELECTED}`)
  await page.getByRole('button', { name: 'node:categorize_bank_lines' }).click()
  const inspector = page.getByRole('complementary')
  await expect(inspector.getByRole('heading', { name: 'node:categorize_bank_lines' })).toBeVisible()
  await expect(inspector.getByText('4,600 in, 400 out')).toBeVisible()
  await expect(inspector.getByRole('link', { name: 'Open the label' })).toHaveAttribute('href', '/labels/lbl_0000000000000006')
  await expect(inspector.getByRole('link', { name: 'Cloud Trace' })).toHaveAttribute('href', /console\.cloud\.google\.com\/traces/)
  await expect(inspector.getByText('Content is not captured in this deployment.')).toBeVisible()
})

test('AC-017-5: other roles are told the page is the owner\'s', async ({ page }) => {
  await serve(page, 'reviewer')
  await page.goto('/preview/runs?role=reviewer')
  await expect(page.getByText('Only the owner of this workspace can see its runs.')).toBeVisible()
})

test('AC-019-4: the runs page stays inside 360 and 1600 px', async ({ page }) => {
  await serve(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/preview/runs/${SELECTED}`)
    await expect(page.getByRole('heading', { name: 'Runs' })).toBeVisible()
    await noOverflow(page)
  }
})
