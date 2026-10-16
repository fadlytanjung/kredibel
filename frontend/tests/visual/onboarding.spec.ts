/**
 * Onboarding with the demo company (spec 021, AC-021-1, AC-021-3): the card and its words like the
 * mock onboarding.html, three widths, axe; opening it posts once and leaves onboarding for the
 * dashboard and its tour. Without a template the card is not offered.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, texts } from './fixtures'

const require = createRequire(import.meta.url)

async function plans(page: Page) {
  await page.route('**/api/plans', (route) =>
    route.fulfill({
      json: {
        plans: [{ id: 'free_trial', label: 'Free trial', status: 'AVAILABLE', trialDays: 30, highlights: [], limits: { documentsPerMonth: 150, extractedPagesPerMonth: 400 } }],
        comingSoonFeatures: [],
        languages: [],
      },
    }),
  )
}

const outline = async (page: Page) => ({
  demo: await texts(page, '.onboard-demo :is(h2, p, .button)'),
  or: await texts(page, '.onboard-or'),
  title: await texts(page, '.onboard-form h1'),
})

test('AC-021-1: onboarding offers the demo company like the mock', async ({ page }) => {
  await plans(page)
  await page.goto('/preview/onboarding?demo=1')
  await expect(page.getByRole('heading', { name: 'Explore a demo company' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await expect(page.locator('.onboard-demo')).toHaveScreenshot('onboarding-demo.png')
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('.onboard-form')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
  const implementation = await outline(page)
  await page.goto(mockUrl('onboarding'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-021-1: opening the demo company posts once and goes to the dashboard', async ({ page }) => {
  await plans(page)
  const posts: string[] = []
  await page.route('**/api/workspaces/demo', (route) => {
    posts.push(route.request().method())
    return route.fulfill({ status: 201, json: { orgId: 'org_demo_copy', name: 'Sunrise Coffee Roasters' } })
  })
  await page.goto('/preview/onboarding?demo=1')
  await page.getByRole('button', { name: 'Open the demo company' }).click()
  await page.waitForURL((url) => !url.pathname.startsWith('/preview/onboarding'))
  expect(posts).toEqual(['POST'])
})

test('AC-021-3: without a template there is no demo card', async ({ page }) => {
  await plans(page)
  await page.goto('/preview/onboarding')
  await expect(page.getByRole('heading', { name: 'Set up your business' })).toBeVisible()
  await expect(page.locator('.onboard-demo')).toHaveCount(0)
})
