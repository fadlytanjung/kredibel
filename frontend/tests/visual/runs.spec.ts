/**
 * Runs page parity with its mock (spec 017, AC-017-5…7; spec 019 AC-019-4): the same synthetic
 * fixture as design/mocks/runs.html and run.html, three widths, 360/1600 bounds, axe. The list in the
 * shared DataTable, and one run in the drawer with its waterfall and inspector, are compared.
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

/** The list as a person sees it: chips, columns, the runs and the pager. */
async function listOutline(page: Page) {
  return {
    headings: await texts(page, '#content .page-head h1'),
    chips: await texts(page, '#content .chips .chip'),
    search: await page.locator('#content .table-search-input').getAttribute('placeholder'),
    columns: await texts(page, '#content .runs-table th:visible'),
    runs: await texts(page, '#content .runs-table tbody strong'),
    statuses: await texts(page, '#content .runs-table .status-line'),
    durations: await texts(page, '#content .runs-table td.r:nth-child(4)'),
    cells: await texts(page, '#content .runs-table td.hide-rt:visible'),
    pager: await texts(page, '#content .pager-line > span:first-child'),
  }
}

/** The open run: its head, the spans on the time axis and the inspector of the selected call. */
async function drawerOutline(page: Page) {
  return {
    head: await texts(page, '.drawer-head :is(span.muted, h1, p)'),
    ticks: await texts(page, '.drawer .span-axis .span-track span'),
    spans: await texts(page, '.drawer .span-row .span-name'),
    spanDurations: await texts(page, '.drawer .span-row .span-dur'),
    spanDetails: await texts(page, '.drawer .span-row .span-detail'),
    inspector: await texts(page, '.drawer .ev-inspector h2, .drawer .ev-inspector dd, .drawer .ev-inspector .button, .drawer .ev-inspector .lp-side p'),
    selectedRow: await texts(page, '#content .runs-table tr.is-selected strong'),
  }
}

test('AC-017-5: the owner sees every run with its calls, tokens, cost and labels like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/runs')
  await expect(page.getByRole('heading', { name: 'Runs' })).toBeVisible()
  await expect(page.locator('.runs-table tbody tr')).toHaveCount(RUNS.items.length)
  await noOverflow(page)
  await expect(page).toHaveScreenshot('runs.png', { fullPage: true })
  await axeClean(page)
  const implementation = await listOutline(page)
  await page.goto(mockUrl('runs'))
  expect(await listOutline(page)).toEqual(implementation)
})

test('AC-017-6: a run opens in a drawer with its waterfall and inspector like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/runs')
  await page.locator('.runs-table tbody tr').first().click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByRole('heading', { name: /document_workflow on ACB_Mar_2026.pdf/ })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`/runs/${SELECTED}$`))
  await noOverflow(page)
  await expect(page).toHaveScreenshot('run.png')
  await axeClean(page)
  const implementation = { ...(await listOutline(page)), ...(await drawerOutline(page)) }
  await page.goto(mockUrl('run'))
  expect({ ...(await listOutline(page)), ...(await drawerOutline(page)) }).toEqual(implementation)
})

test('AC-017-6: Esc closes the run and keeps the list', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/runs/${SELECTED}`)
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('.runs-table tbody tr')).toHaveCount(RUNS.items.length)
})

test('AC-017-6: selecting a span shows its call; the trace link and the label are one click away', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/runs/${SELECTED}`)
  await page.getByRole('button', { name: 'node:categorize_bank_lines' }).click()
  const inspector = page.getByRole('dialog').getByRole('complementary')
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
