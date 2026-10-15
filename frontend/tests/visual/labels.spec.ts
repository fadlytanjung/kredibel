/**
 * Labels page parity with its mock (spec 016, AC-016-5, AC-016-6; spec 019 AC-019-4): the same
 * synthetic fixture as design/mocks/labels.html, three widths, 360/1600 bounds, axe. The lead
 * sentence, the task switch, the status chips, every row and the open panel are compared.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { LABELS, mockUrl, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)
const OPEN = LABELS.items[3].labelId // the Roastline category, as the mock opens it

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    const one = path.match(/^\/api\/labels\/(lbl_\w+)$/)
    if (path === '/api/labels') return route.fulfill({ json: LABELS })
    if (one) return route.fulfill({ json: LABELS.items.find((i) => i.labelId === one[1]) })
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

/** The page as a person sees it: lead, task switch, chips, each row's words and the panel. */
async function outline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2):visible'),
    lead: await texts(page, '#content .page-head p'),
    tasks: await texts(page, '#content .seg button'),
    chips: await texts(page, '#content .chips .chip'),
    bulk: await texts(page, '#content .bulk-bar strong'),
    columns: await texts(page, '#content .lbl-table th:visible'),
    subjects: await texts(page, '#content .lbl-table .lbl-subj strong'),
    pageChips: (await texts(page, '#content .lbl-table .pchip')).map((s) => s.replace(/\s/g, '')),
    values: await texts(page, '#content .lbl-table .lbl-val'),
    taskWords: await texts(page, '#content .lbl-table .task'),
    confidence: await texts(page, '#content .lbl-table .conf'),
    statuses: await texts(page, '#content .lbl-table .lbl-status'),
    sources: await texts(page, '#content .lbl-table td.small.muted:visible'),
    datasets: await texts(page, '#content .lbl-table .ds:visible'),
    panelHead: await texts(page, '#content .lbl-panel .lp-head > span'),
    panelAi: await texts(page, '#content .lbl-panel .lp-ai strong'),
    panelFields: await texts(page, '#content .lbl-panel .field label'),
    panelProvenance: await texts(page, '#content .lbl-panel .lp-prov dt'),
    panelActions: await texts(page, '#content .lbl-panel .lp-actions .button'),
    foot: await texts(page, '#content .lbl-foot p'),
  }
}

test('AC-016-5: the labels page lists every AI decision with its confidence and status like the mock', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/labels/${OPEN}`)
  await expect(page.getByRole('heading', { name: 'Labels' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'TRANSFER OUT ROASTLINE EQUIPMENT' })).toBeVisible()
  await noOverflow(page)
  await expect(page).toHaveScreenshot('labels.png', { fullPage: true, mask: [page.locator('select')] })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('labels'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-016-6: a correction is one at a time, with a note and the remembered rule', async ({ page }) => {
  await serve(page)
  let sent: unknown = null
  await page.route(`**/api/labels/${OPEN}/decision`, (route) => {
    sent = route.request().postDataJSON()
    const decided = { ...LABELS.items[3], status: 'CORRECTED', final: { value: 'INVENTORY_PURCHASE', source: 'PERSON' }, decidedBy: 'Maya Sari', decidedAt: '2026-07-16T10:00:00Z', needsCheck: false }
    return route.fulfill({ json: decided })
  })
  await page.goto(`/preview/labels/${OPEN}`)
  const panel = page.getByRole('complementary')
  await expect(panel.getByRole('button', { name: 'Save correction' })).toBeDisabled()
  await panel.getByLabel('Category').selectOption('INVENTORY_PURCHASE')
  await expect(panel.getByRole('button', { name: 'Confirm' })).toBeDisabled()
  await panel.getByLabel(/^Note/).fill('Beans for roasting')
  await panel.getByRole('button', { name: 'Save correction' }).click()
  await expect.poll(() => sent).toEqual({ action: 'CORRECT', value: 'INVENTORY_PURCHASE', note: 'Beans for roasting', applyToSimilar: true })
})

test('AC-019-4: the labels page stays inside 360 and 1600 px', async ({ page }) => {
  await serve(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/preview/labels/${OPEN}`)
    await expect(page.getByRole('heading', { name: 'Labels' })).toBeVisible()
    await noOverflow(page)
  }
})
