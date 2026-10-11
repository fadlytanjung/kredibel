import { test, expect } from '@playwright/test'

test.describe('Visual Regression: Login Page', () => {
  test('login page matches baseline', async ({ page }) => {
    await page.goto('/login')
    await page.waitForSelector('input[type="email"]')
    await expect(page).toHaveScreenshot('login.png')
  })
})

test.describe('Visual Regression: AppShell & Dashboard', () => {
  test('app shell and dashboard match baseline', async ({ page }) => {
    await page.goto('/preview/shell')
    await page.waitForSelector('text=Upload your first documents')
    await expect(page).toHaveScreenshot('app-shell.png')
  })
})

test.describe('Visual Regression: Onboarding', () => {
  test('onboarding matches baseline', async ({ page }) => {
    await page.route('**/api/plans', (route) =>
      route.fulfill({
        json: {
          plans: [
            {
              id: 'free_trial',
              label: 'Free trial',
              status: 'AVAILABLE',
              trialDays: 30,
              highlights: [],
              limits: { documentsPerMonth: 150, extractedPagesPerMonth: 400 },
            },
          ],
          comingSoonFeatures: [],
          languages: [],
        },
      }),
    )
    await page.goto('/preview/onboarding')
    await page.waitForSelector('text=30-day free trial')
    // The time zone defaults to the browser's; pin it so baselines do not depend on the machine.
    await page.selectOption('#timezone', 'Asia/Jakarta')
    await expect(page).toHaveScreenshot('onboarding.png', { fullPage: true })
  })
})
