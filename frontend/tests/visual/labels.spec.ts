/**
 * Labels page parity with its mock (spec 016, AC-016-5, AC-016-6; spec 019 AC-019-4): the same
 * synthetic fixture as design/mocks/labels.html and label.html, three widths, 360/1600 bounds, axe.
 * The lead sentence, the task switch, the shared table's chips and rows, and the open drawer are compared.
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
    const md = (LABELS.extractions as Record<string, string>)[path]
    if (md !== undefined) return route.fulfill({ body: md, contentType: 'text/markdown; charset=utf-8' })
    if (path.endsWith('/extraction.md')) return route.fulfill({ status: 404, json: { code: 'NOT_FOUND' } })
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

/** The list as a person sees it: lead, task switch, chips, each row's words and the pager. */
async function listOutline(page: Page) {
  return {
    headings: await texts(page, '#content .page-head h1'),
    lead: await texts(page, '#content .page-head p'),
    tasks: await texts(page, '#content .seg button'),
    chips: await texts(page, '#content .chips .chip'),
    search: await page.locator('#content .table-search-input').getAttribute('placeholder'),
    actions: await texts(page, '#content .table-actions > *'),
    columns: await texts(page, '#content .lbl-table th:visible'),
    subjects: await texts(page, '#content .lbl-table .lbl-subj strong'),
    pageChips: (await texts(page, '#content .lbl-table .pchip')).map((s) => s.replace(/\s/g, '')),
    values: await texts(page, '#content .lbl-table .lbl-val'),
    taskWords: await texts(page, '#content .lbl-table .task'),
    confidence: await texts(page, '#content .lbl-table .conf'),
    statuses: await texts(page, '#content .lbl-table .lbl-status'),
    sources: await texts(page, '#content .lbl-table td.small.muted:visible'),
    datasets: await texts(page, '#content .lbl-table .ds:visible'),
    extractionLinks: await texts(page, '#content .lbl-table .md-link'),
    pager: await texts(page, '#content .pager-line > span'),
    foot: await texts(page, '#content .lbl-foot p'),
  }
}

/** The open label: its head, the decision, the extraction and the provenance. */
async function drawerOutline(page: Page) {
  return {
    head: await texts(page, '.drawer-head :is(.lp-head > span, h1, p)'),
    ai: await texts(page, '.drawer .lp-ai strong'),
    fields: await texts(page, '.drawer .field label'),
    provenance: await texts(page, '.drawer .lp-prov dt'),
    extraction: await texts(page, '.drawer .lp-md summary, .drawer .lp-md pre'),
    actions: await texts(page, '.drawer .lp-actions .button'),
    selectedRow: await texts(page, '#content .lbl-table tr.is-selected .lbl-subj strong'),
  }
}

test('AC-016-5: the labels page lists every AI decision with its confidence and status like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/labels')
  await expect(page.getByRole('heading', { name: 'Labels' })).toBeVisible()
  await expect(page.locator('.lbl-table tbody tr')).toHaveCount(10)
  await noOverflow(page)
  await expect(page).toHaveScreenshot('labels.png', { fullPage: true })
  await axeClean(page)
  const implementation = await listOutline(page)
  await page.goto(mockUrl('labels'))
  expect(await listOutline(page)).toEqual(implementation)
})

test('AC-016-6: a label opens in a drawer with its extraction like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/labels')
  await page.getByRole('row', { name: /TRANSFER OUT ROASTLINE EQUIPMENT/ }).click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByRole('heading', { name: 'TRANSFER OUT ROASTLINE EQUIPMENT' })).toBeVisible()
  await expect(page).toHaveURL(new RegExp(`/labels/${OPEN}$`))
  await expect(drawer.locator('.lp-md pre')).toContainText('MERIDIAN SAVINGS ••••7720')
  await noOverflow(page)
  await expect(page).toHaveScreenshot('label.png', { mask: [page.locator('select')] })
  await axeClean(page)
  const implementation = { ...(await listOutline(page)), ...(await drawerOutline(page)) }
  await page.goto(mockUrl('label'))
  expect({ ...(await listOutline(page)), ...(await drawerOutline(page)) }).toEqual(implementation)
  await page.goto(`/preview/labels/${OPEN}`)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
})

test('AC-016-1: books read before labels existed get theirs from one button', async ({ page }) => {
  let synced = false
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/labels/sync') {
      synced = true
      return route.fulfill({ json: { created: 1284 } })
    }
    if (path === '/api/labels') return route.fulfill({ json: synced ? LABELS : { items: [], nextCursor: null, summary: { ...LABELS.summary, total: 0, needsCheck: 0, verified: 0, corrected: 0, aiAgreementOnChecked: null, byTask: {}, byStatus: {} } } })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    return route.fulfill({ json: { items: [] } })
  })
  await page.goto('/preview/labels')
  await expect(page.getByText('Books read before labels existed have none yet.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Create labels from your books' }).first().click()
  await expect(page.getByRole('status')).toHaveText('1,284 labels created from your books.')
  await expect(page.locator('.lbl-table tbody tr')).toHaveCount(10)
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
  const panel = page.getByRole('dialog')
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
