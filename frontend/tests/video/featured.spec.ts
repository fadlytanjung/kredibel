/**
 * Records the 90-second cut (tools/video/featured/narration.json) on production with the public demo
 * account (synthetic data, docs/25): the problem, the books read and checked, a risk with its
 * evidence, the loan readiness report (spec 025), the Google AI tools and who it helps. The camera
 * scene is a placeholder card here; edit.py --camera puts the presenter's own clip in its place, under
 * the name tag drawn below (out-featured/name-tag.png).
 *
 * Run: make video-featured (VIDEO_CUT=featured). Not part of `make check`.
 */
import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {
  card,
  closeDrawer,
  EMAIL,
  glide,
  idToken,
  JULY,
  OUT,
  overlay,
  PACK,
  PASSWORD,
  press,
  resetDemo,
  ROOT,
  Scene,
  scrollTo,
  sleep,
} from './recorder'

const PLAN = JSON.parse(fs.readFileSync(path.join(ROOT, 'tools/video/featured/narration.json'), 'utf8')) as {
  presenter: { name: string; role: string }
}

/** The presenter's name tag, a transparent 1920x1080 PNG laid over the camera clip by edit.py. */
async function nameTag(page: import('@playwright/test').Page) {
  const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`)
  await page.setContent(`<!doctype html><html><head><style>
    @font-face{font-family:"Archivo Variable";font-weight:100 900;font-stretch:62% 125%;
      src:url(${path.join(ROOT, 'design/mocks/assets/fonts/archivo-latin-wdth-normal.woff2')}) format("woff2-variations")}
    html,body{margin:0;width:1920px;height:1080px;background:transparent}
    .tag{position:absolute;left:96px;bottom:96px;padding:22px 34px 24px 30px;border-radius:18px;background:rgba(22,33,43,.86);
      border-left:8px solid #2E8B6A;color:#fff;font-family:"Archivo Variable",system-ui,sans-serif}
    .n{font-size:44px;font-weight:700;font-stretch:108%;letter-spacing:-.005em}
    .r{margin-top:6px;font-size:28px;color:rgba(255,255,255,.78)}
  </style></head><body><div class="tag"><div class="n">${esc(PLAN.presenter.name)}</div><div class="r">${esc(PLAN.presenter.role)}</div></div></body></html>`)
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({ path: path.join(OUT, 'name-tag.png'), omitBackground: true })
}

test('record the 90-second cut', async ({ page, baseURL }) => {
  const origin = baseURL ?? 'https://kredibel-app.web.app'
  await nameTag(page)
  await resetDemo(origin)
  await page.context().addInitScript(overlay)
  const cdp = await page.context().newCDPSession(page)
  const content = page.locator('#content')

  await card(page, cdp, 'camera')
  await card(page, cdp, 'problem')
  await card(page, cdp, 'intro')

  // Signed in off camera; a fresh copy asks the welcome question first.
  await page.goto('/login')
  await page.getByLabel('Email address').fill(EMAIL)
  await page.getByLabel(/Password/).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('button', { name: /Keep my books/ }).click({ timeout: 60_000 })
  await expect(page.getByRole('heading', { name: 'Sunrise Coffee Roasters', level: 1 })).toBeVisible({ timeout: 60_000 })

  // Files in any order: a copy is never read again; Gemini reads, code checks each value on the page.
  await page.goto('/documents')
  await expect(content.getByText('statement-2026-10.pdf').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  let scene = new Scene(page, cdp, 'read')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.getByText('Choose files').first(), 600)
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles([
      path.join(JULY, 'inv-sales-2026-07-04.pdf'),
      path.join(JULY, 'receipt-2026-07-01.jpg'),
      path.join(PACK, 'statement-2026-10.pdf'),
    ])
  const tray = content.locator('.tray-list')
  const notice = content.getByText(/Not read again and not counted/).first()
  await scene.cut(() => expect(notice).toBeVisible({ timeout: 60_000 }))
  await glide(page, notice, 700)
  await scene.say(1)
  const invoiceRow = tray.locator('li', { hasText: 'inv-sales-2026-07-04' })
  await scene.cut(() => expect(invoiceRow.getByText(/^Read as/)).toBeVisible({ timeout: 300_000 }))
  await press(page, invoiceRow.getByRole('link', { name: 'Open' }), 600)
  const total = content.locator('button', { hasText: /^Total/ }).first()
  await scene.cut(() => expect(total).toBeVisible({ timeout: 60_000 }))
  await press(page, total, 700)
  await sleep(500)
  await glide(page, total.getByText('On the page'), 600)
  await scene.end(0.8)

  // A month's risk with its evidence: the amount edited in a PDF editor.
  await page.goto('/risk')
  await expect(content.getByText('M04').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'risk')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.locator(':is(a,button)').filter({ hasText: /^Aug\s*2026/ }).first(), 700)
  const font = content.locator('tr', { hasText: 'M04' }).first()
  await scrollTo(font, 0.4)
  await scene.say(1)
  await press(page, font.getByText('M04'), 600)
  await scene.cut(async () => {
    const image = page.getByRole('dialog').locator('img').first()
    await expect(image).toBeVisible({ timeout: 30_000 })
    await expect.poll(() => image.evaluate((img) => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0), { timeout: 30_000 }).toBe(true)
    await sleep(600)
  })
  await glide(page, page.getByRole('dialog').getByRole('heading').first(), 700)
  await scene.end(0.6)

  // New: the loan readiness report, from the menu. Off camera, the month the late upload reopened
  // reconciles again first (a minute or two), so the report shows the books as they settle.
  await closeDrawer(page)
  const token = await idToken(origin)
  await expect
    .poll(
      async () => {
        const res = await fetch(`${origin}/api/readiness`, { headers: { Authorization: `Bearer ${token}` } })
        const body = (await res.json()) as { checks?: { id: string; status: string }[] }
        return body.checks?.find((c) => c.id === 'RECONCILED')?.status
      },
      { timeout: 300_000, intervals: [5_000] },
    )
    .toBe('PASS')
    .catch(() => undefined)
  await sleep(600)
  scene = new Scene(page, cdp, 'readiness')
  await scene.begin()
  await scene.say(0)
  await press(page, page.getByRole('link', { name: 'Loan readiness' }).first(), 800)
  const verdict = content.locator('.ready-verdict-head')
  await scene.cut(() => expect(verdict.getByRole('heading', { level: 2 })).toBeVisible({ timeout: 60_000 }))
  await glide(page, verdict.locator('.badge').first(), 600)
  await scene.say(1)
  await glide(page, verdict.getByRole('heading', { level: 2 }), 700, 0.3)
  const findings = content.locator('.ready-check', { hasText: 'No open risks' })
  await scrollTo(findings, 0.3)
  await glide(page, findings.locator('.ready-findings .link').first(), 800, 0.3)
  await scene.say(2)
  await scrollTo(content.getByRole('heading', { name: 'At a glance' }), 0.15)
  await glide(page, content.locator('.ledger-figures > div').nth(4), 700)
  await scrollTo(content.getByRole('heading', { name: 'Loan readiness', level: 1 }), 0.05)
  // Headless Chrome has no print dialog: the page is shown as it prints, without the menus.
  await page.evaluate(() => (window.print = () => undefined))
  await press(page, page.getByRole('button', { name: 'Print or save as PDF' }), 600)
  await page.emulateMedia({ media: 'print' })
  await sleep(2400)
  await page.emulateMedia({ media: 'screen' })
  await scene.end(0.3)

  await card(page, cdp, 'tools')
  await card(page, cdp, 'close')
})
