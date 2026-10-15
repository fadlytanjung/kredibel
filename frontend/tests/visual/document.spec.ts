/**
 * Document page parity with its mocks (spec 019, T019-03, AC-019-3, AC-019-4; spec 003 AC-003-9,
 * spec 005 T005-11): a read statement beside its page, and a ledger export with its planned
 * column confirmation identified as such.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { DOCUMENT, mockUrl, pageImageFromMock, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)

type Line = (typeof DOCUMENT.lines)[number]

async function serve(page: Page, doc: Record<string, unknown>, lines: Line[], png?: Buffer) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === `/api/documents/${doc.docId}`) return route.fulfill({ json: doc })
    if (path.startsWith(`/api/documents/${doc.docId}/pages/`) && png) return route.fulfill({ body: png, contentType: 'image/png' })
    if (path === '/api/bank-lines') return route.fulfill({ json: { items: lines, nextCursor: null } })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    return route.fulfill({ json: { items: [] } })
  })
}

/** What a person sees on the document page: its header, figures, tabs, filters and columns. */
async function outline(page: Page) {
  return {
    title: await texts(page, '#content h1'),
    status: await texts(page, '#content .doc-status .badge'),
    actions: await texts(page, '#content .doc-status .button'),
    viewer: await page.locator('#content .viewer-bar [role="group"]').evaluateAll((els) => els.map((el) => el.getAttribute('aria-label'))),
    figures: await texts(page, '#content .doc-pane .ledger-figures dt'),
    tabs: await texts(page, '#content [role="tab"]', true),
    chips: await texts(page, '#content .chips .chip', true),
    columns: await texts(page, '#content .data-table th'),
    legend: await texts(page, '#content .reading-legend'),
  }
}

async function axeClean(page: Page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
}

async function openStatement(page: Page) {
  // The page image is the mock's synthetic statement page; its lit value gives the selected line's box.
  const { png, box } = await pageImageFromMock(page, 'document')
  const lines = DOCUMENT.lines.map((line) =>
    line.txId === 'tx_feb_09' && box ? { ...line, readings: { amount: { ...line.readings.amount, bbox: box } } } : line,
  )
  await serve(page, DOCUMENT.document, lines, png)
  await page.goto('/preview/documents/doc_feb')
  await expect(page.getByRole('heading', { name: 'ACB_Feb_2026.pdf' })).toBeVisible()
  await page.getByRole('row', { name: /TRANSFER IN DAYBREAK CAFE/ }).click()
  await expect(page.getByText('The box shows where the selected value is printed, from the word positions in the file itself.')).toBeVisible()
  await expect(page.locator('.page-zoom img')).toBeVisible()
  // Lighting the value scrolls the viewer into view; the baseline starts at the top of the page.
  await page.evaluate(() => window.scrollTo(0, 0))
}

test('AC-019-3: a read statement shows its page beside what was read, like the mock', async ({ page }) => {
  await openStatement(page)
  await expect(page).toHaveScreenshot('document.png', { fullPage: true })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('document'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-019-3: a ledger export shows its rows and period; the column confirmation is marked as planned', async ({ page }) => {
  await serve(page, DOCUMENT.ledger, [])
  await page.goto('/preview/documents/doc_gl')
  await expect(page.getByRole('heading', { name: 'GL_2026_Q1.csv' })).toBeVisible()
  await expect(page.getByText('52 general-ledger rows imported')).toBeVisible()
  await expect(page.getByRole('link', { name: 'View in Profit and loss' })).toHaveAttribute('href', '/profit-loss')
  await expect(page).toHaveScreenshot('document-ledger.png', { fullPage: true })
  await axeClean(page)
  const read = async () => ({
    title: await texts(page, '#content h1'),
    status: await texts(page, '#content .doc-status .badge'),
    figures: await texts(page, '#content .doc-pane .ledger-figures dt'),
    tabs: await texts(page, '#content .doc-pane [role="tab"]', true),
    links: await texts(page, '#content .doc-pane .button, #content .doc-pane .badge-brand'),
  })
  const implementation = await read()
  // The app has no column confirmation yet (T005-11): the mock keeps it, labelled as planned.
  expect(await page.getByRole('button', { name: 'Confirm columns' }).count()).toBe(0)
  await page.goto(mockUrl('document-ledger'))
  expect(await read()).toEqual(implementation)
  await expect(page.locator('[data-planned="T005-11"]')).toContainText('Planned, spec 005 T005-11')
})

test('AC-019-4: the document page stays inside 360 and 1600 px with usable tabs', async ({ page }) => {
  await openStatement(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const details = page.getByRole('tab', { name: 'Details' })
    await details.click()
    await expect(details).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByText('Archipelago Commerce Bank', { exact: true })).toBeVisible()
    await page.getByRole('tab', { name: /Transactions/ }).click()
  }
})
