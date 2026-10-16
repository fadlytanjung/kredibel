/**
 * Documents upload tray parity with its mock (spec 003, AC-003-1, AC-003-6; spec 019 AC-019-4):
 * the same synthetic uploads as design/mocks/documents.html (contracts/design/fixtures/documents.json),
 * three widths, 360/1600 bounds, axe. Each row's file, sentence and next step is compared.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, texts, UPLOADS, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)

async function serve(page: Page) {
  await page.clock.setFixedTime(new Date(UPLOADS.now))
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/documents') return route.fulfill({ json: { items: UPLOADS.items, nextCursor: null } })
    if (path === '/api/review-items') return route.fulfill({ json: { items: UPLOADS.reviewItems, nextCursor: null } })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    return route.fulfill({ json: { items: [] } })
  })
}

/** The tray as a person sees it: the drop area, then each row's file, sentence and next step. */
async function outline(page: Page) {
  return {
    drop: await texts(page, '#content .tray-drop :is(strong, .button):visible'),
    list: await page.locator('#content .tray-list').getAttribute('aria-label'),
    files: await texts(page, '#content .tray-list .f'),
    sentences: await texts(page, '#content .tray-list .m'),
    links: await texts(page, '#content .tray-list .m a'),
    actions: await texts(page, '#content .tray-list .act a'),
    tones: await page.locator('#content .tray-list .file-ico').evaluateAll((els) => els.map((el) => el.className)),
    progress: await page.locator('#content .tray-list .pbar i').evaluateAll((els) => els.map((el) => (el as HTMLElement).style.width)),
  }
}

test('AC-003-6: the tray shows each upload\'s state and next step like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/documents')
  await expect(page.locator('.tray-list > li')).toHaveCount(4)
  await expect(page.getByRole('link', { name: 'Decide' })).toHaveAttribute('href', '/review/itm_rcp_0617_2')
  await expect(page.getByRole('link', { name: 'Check columns' })).toHaveAttribute('href', '/review/itm_ledger_h1')
  await expect(page.locator('.tray-list').getByRole('link', { name: 'ACB_Feb_2026.pdf' })).toHaveAttribute('href', '/documents/doc_feb')
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await expect(page.locator('.tray')).toHaveScreenshot('documents-tray.png')
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
  const implementation = await outline(page)
  await page.goto(mockUrl('documents'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-003-6: after a day only what waits for a person stays', async ({ page }) => {
  await serve(page)
  await page.clock.setFixedTime(new Date('2026-07-12T09:30:00Z'))
  await page.goto('/preview/documents')
  await expect(page.locator('.tray-list .f')).toHaveText(['Receipt 0617 (2).jpg', 'ledger-2026-H1.csv'])
})

test('AC-019-4: the documents page stays inside 360 and 1600 px', async ({ page }) => {
  await serve(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preview/documents')
    await expect(page.locator('.tray-list > li')).toHaveCount(4)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  }
})
