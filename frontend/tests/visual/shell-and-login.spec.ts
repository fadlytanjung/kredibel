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
