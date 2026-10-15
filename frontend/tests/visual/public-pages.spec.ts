import { test, expect, type Page } from '@playwright/test'

// Public pages (spec 020). Baselines are recorded on the CI image (`make test-visual`); the landing
// is the logged-out entry, so no session or network is needed. The pages are shot with reduced motion
// so every depth scene is settled and nothing waits for a scroll reveal (docs/12 §12, AC-020-12).
test.use({ reducedMotion: 'reduce' })

async function settle(page: Page) {
  await page.evaluate(() => document.fonts.ready)
}

test.describe('Visual Regression: Landing', () => {
  test('landing page matches baseline', async ({ page }) => {
    await page.goto('/')
    await page.waitForSelector('text=Every number has a source.')
    await settle(page)
    await expect(page).toHaveScreenshot('landing.png', { fullPage: true, animations: 'disabled' })
  })
})

test.describe('Visual Regression: Pricing', () => {
  test('pricing page matches baseline', async ({ page }) => {
    await page.goto('/pricing')
    await page.waitForSelector('text=Free while we build.')
    await settle(page)
    await expect(page).toHaveScreenshot('pricing.png', { fullPage: true, animations: 'disabled' })
  })
})
