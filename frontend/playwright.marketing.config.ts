import { defineConfig } from '@playwright/test'

/**
 * Captures the public site's product screenshots (spec 020, T020-31) from the app's synthetic preview
 * routes: `npm run marketing:shots`. Not a test suite; it writes `public/marketing/*.png`.
 * `PLAYWRIGHT_CHROMIUM_EXECUTABLE` points at a local Chromium when Playwright's own is not installed.
 */
export default defineConfig({
  testDir: './tests/marketing',
  reporter: 'list',
  retries: 0,
  use: {
    baseURL: 'http://localhost:5173',
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE }
      : {},
  },
  webServer: {
    command: 'npm run dev -- --port 5173',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
  },
})
