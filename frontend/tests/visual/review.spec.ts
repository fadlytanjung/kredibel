/**
 * Review parity with its mocks (spec 019, T019-03, AC-019-3, AC-019-4; spec 009, T009-06,
 * AC-009-2, AC-009-4, AC-009-7): the queue, the proposal drawer, and a value correction beside the
 * receipt's page. The same synthetic items as the mocks (contracts/design/fixtures/review.json).
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, pageImageFromMock, REVIEW, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)
const PROPOSAL = 'itm_0000000000000001'
const VALUE = 'itm_0000000000000009'

async function serve(page: Page, png?: Buffer) {
  const countsByKind = Object.fromEntries(REVIEW.items.map((i) => [i.kind, REVIEW.items.filter((o) => o.kind === i.kind).length]))
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const month = url.searchParams.get('month')
    const byMonth = <T extends { month?: string }>(items: T[]) => items.filter((i) => !month || i.month === month)
    const one = path.match(/^\/api\/review-items\/(itm_\w+)$/)
    const doc = path.match(/^\/api\/documents\/(doc_\w+)$/)
    if (path === '/api/review-items') return route.fulfill({ json: { items: REVIEW.items, countsByKind, nextCursor: null } })
    if (one) return route.fulfill({ json: REVIEW.items.find((i) => i.itemId === one[1]) })
    if (doc) return route.fulfill({ json: REVIEW.documents[doc[1] as keyof typeof REVIEW.documents] })
    if (/^\/api\/documents\/doc_\w+\/pages\//.test(path) && png) return route.fulfill({ body: png, contentType: 'image/png' })
    if (path === '/api/bank-lines') return route.fulfill({ json: { items: byMonth(REVIEW.lines), nextCursor: null } })
    if (path === '/api/invoices') return route.fulfill({ json: { items: byMonth(REVIEW.invoices) } })
    if (path === '/api/receipts') return route.fulfill({ json: { items: byMonth(REVIEW.receipts) } })
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

/** The queue as a person sees it: title, chips, columns and every item with its kind. */
async function queueOutline(page: Page) {
  return {
    headings: await texts(page, '#content h1'),
    chips: await texts(page, '#content .chips .chip', true),
    columns: await texts(page, '#content .data-table th'),
    items: await texts(page, '#content .qitem .t'),
    kinds: await texts(page, '#content .qitem .s'),
    pager: await texts(page, '#content .pager-line'),
  }
}

/** The fix drawer: the kind and month, the title and why, the subjects, the reasons, the actions. */
async function drawerOutline(page: Page) {
  const drawer = '#content [role="dialog"]'
  return {
    head: await texts(page, `${drawer} .fix-head .badge, ${drawer} .fix-head .pager-line > span > span:not(.badge)`),
    title: await texts(page, `${drawer} h2`),
    why: await texts(page, `${drawer} .fix-head p`),
    subjects: await texts(page, `${drawer} .subject .t`),
    reasons: await texts(page, `${drawer} .why-tag`),
    labels: await texts(page, `${drawer} .label`),
    actions: await texts(page, `${drawer} .other-actions .button, ${drawer} form .button, ${drawer} .fix-foot .button`),
  }
}

test.describe('Review (spec 009, T009-06; spec 019, T019-03)', () => {
  test('the queue matches its baseline and its mock', async ({ page }) => {
    await serve(page)
    await page.goto('/preview/review')
    await expect(page.getByText('Confirm the payment of IDR 18,700,000 on 9 Feb 2026')).toBeVisible()
    await expect(page).toHaveScreenshot('review-queue.png', { fullPage: true })
    await axeClean(page)
    const implementation = await queueOutline(page)
    await page.goto(mockUrl('review'))
    expect(await queueOutline(page)).toEqual(implementation)
  })

  test('a proposal opens in the fix drawer like the mock', async ({ page }) => {
    await serve(page)
    await page.goto(`/preview/review/${PROPOSAL}`)
    const drawer = page.getByRole('dialog')
    await expect(drawer.getByText('TRANSFER IN DAYBREAK CAFE')).toBeVisible()
    await expect(drawer.getByRole('button', { name: 'Confirm the match' })).toBeVisible()
    await expect(page).toHaveScreenshot('review-proposal.png', { fullPage: true })
    await axeClean(page)
    const implementation = await drawerOutline(page)
    await page.goto(mockUrl('review-match'))
    expect(await drawerOutline(page)).toEqual(implementation)
  })

  test('a value to check shows the receipt beside the panel and corrects it as printed', async ({ page }) => {
    const { png } = await pageImageFromMock(page, 'review-correction', '.doc-receipt')
    await serve(page, png)
    await page.goto(`/preview/review/${VALUE}`)
    const drawer = page.getByRole('dialog')
    await expect(drawer.getByText('Receipt 0617')).toBeVisible()
    await expect(drawer.locator('.page-zoom img')).toBeVisible()
    await drawer.getByRole('button', { name: 'Correct it' }).click()
    const field = drawer.getByLabel('The total as printed')
    await expect(field).toBeVisible()
    await expect(page).toHaveScreenshot('review-correction.png', { fullPage: true })
    await axeClean(page)
    const implementation = await drawerOutline(page)
    await field.fill('820000.00')
    await expect(drawer.getByRole('button', { name: 'Save the correction' })).toBeEnabled()
    // Keys are the queue's only while nobody is typing; Esc closes the drawer once the field is left.
    await field.blur()
    await page.keyboard.press('Escape')
    await expect(drawer).toHaveCount(0)
    await page.goto(mockUrl('review-correction'))
    expect(await drawerOutline(page)).toEqual(implementation)
  })

  test('AC-019-4: the queue and the drawer stay inside 360 and 1600 px', async ({ page }) => {
    await serve(page)
    await page.goto(`/preview/review/${PROPOSAL}`)
    await expect(page.getByRole('dialog').getByRole('button', { name: 'Confirm the match' })).toBeVisible()
    for (const width of [360, 1600]) {
      await page.setViewportSize({ width, height: 1000 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      const confirm = page.getByRole('dialog').getByRole('button', { name: 'Confirm the match' })
      const box = await confirm.boundingBox()
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(40)
    }
  })
})
