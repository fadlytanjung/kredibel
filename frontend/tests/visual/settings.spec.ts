/**
 * Settings › Profile parity with its mock (spec 013 AC-013-14; spec 016 AC-016-8; spec 019
 * AC-019-4): the same synthetic workspace as design/mocks/settings-profile.html, three widths,
 * 360/1600 bounds, axe. The framework switch is part of the profile and is saved with it.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)
const PROFILE_WORKSPACE = {
  ...WORKSPACE,
  timezone: 'Asia/Jakarta',
  entityType: 'COMPANY',
  defaultLanguage: 'en',
  profile: { legalName: 'Sunrise Coffee Roasters', accountingFramework: 'IFRS', aliases: [] },
}

async function serve(page: Page, sent: unknown[] = []) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/workspace' && route.request().method() === 'PATCH') {
      const body = route.request().postDataJSON()
      sent.push(body)
      return route.fulfill({ json: { ...PROFILE_WORKSPACE, profile: { ...PROFILE_WORKSPACE.profile, ...body.profile } } })
    }
    if (path === '/api/workspace') return route.fulfill({ json: PROFILE_WORKSPACE })
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

/** The section as a person sees it: subnav, field labels, hints, the framework switch, the button. */
async function outline(page: Page) {
  return {
    headings: await texts(page, '#content h1'),
    subnav: await texts(page, '#content .subnav a'),
    labels: await texts(page, '#content form .field > label, #content form .field > .label'),
    hints: await texts(page, '#content form .field > .hint'),
    frameworks: await texts(page, '#content form .seg button'),
    pressed: await texts(page, '#content form .seg button[aria-pressed="true"]'),
    buttons: await texts(page, '#content form button[type="submit"]'),
  }
}

test('AC-016-8: the profile offers IFRS or US GAAP beside the workspace details, like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/settings/profile')
  await expect(page.getByRole('group', { name: 'Accounting framework' })).toBeVisible()
  await expect(page.getByLabel('Legal name')).toHaveValue('Sunrise Coffee Roasters')
  await noOverflow(page)
  await expect(page).toHaveScreenshot('settings-profile.png', { fullPage: true, mask: [page.locator('select')] })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('settings-profile'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-016-8: choosing US GAAP saves it with the profile and says every month is reclassified', async ({ page }) => {
  const sent: unknown[] = []
  await serve(page, sent)
  await page.goto('/preview/settings/profile')
  await page.getByRole('button', { name: 'US GAAP' }).click()
  await expect(page.getByRole('button', { name: 'US GAAP' })).toHaveAttribute('aria-pressed', 'true')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('status')).toHaveText('Saved. Every month is being reclassified under US GAAP.')
  expect(sent).toHaveLength(1)
  expect((sent[0] as { profile: { accountingFramework: string } }).profile.accountingFramework).toBe('US_GAAP')
})

test('AC-019-4: the profile section stays inside 360 and 1600 px', async ({ page }) => {
  await serve(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preview/settings/profile')
    await expect(page.getByRole('group', { name: 'Accounting framework' })).toBeVisible()
    await noOverflow(page)
  }
})
