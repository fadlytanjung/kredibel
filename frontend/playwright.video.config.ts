/**
 * The demo video's recording (tools/video): one long run against production with the public demo
 * account. Not part of the visual tests; run it with `make video`.
 */
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/video',
  timeout: 20 * 60 * 1000,
  workers: 1,
  reporter: 'line',
  use: {
    baseURL: process.env.VIDEO_BASE_URL ?? 'https://kredibel-app.web.app',
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    colorScheme: 'light',
    locale: 'en-US',
    timezoneId: 'Asia/Jakarta',
    actionTimeout: 15_000,
  },
})
