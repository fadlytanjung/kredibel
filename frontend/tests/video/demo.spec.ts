/**
 * Records the demo video's scenes (tools/video/narration.json) on production with the public demo
 * account (synthetic data, docs/25), with the shared recorder (recorder.ts). tools/video/edit.py turns
 * the frames into the film.
 *
 * Run: make video (narrate, record, edit). Not part of `make check`.
 */
import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import {
  card,
  closeDrawer,
  cursor,
  EMAIL,
  FRAMES,
  glide,
  JULY,
  OUT,
  overlay,
  ownerSession,
  PACK,
  PASSWORD,
  press,
  resetDemo,
  resetMouse,
  Scene,
  scrollTo,
  sleep,
  TIMINGS,
  typeInto,
} from './recorder'

test('record the demo video', async ({ page, browser, baseURL }) => {
  const origin = baseURL ?? 'https://kredibel-app.web.app'
  // VIDEO_SCENES=problem,close re-records only those title cards (no reset, no app scenes).
  const only = (process.env.VIDEO_SCENES ?? '').split(',').filter(Boolean)
  if (only.length) {
    const cdp = await page.context().newCDPSession(page)
    for (const id of only) {
      if (TIMINGS.find((t) => t.id === id)?.kind !== 'card') throw new Error(`${id} is not a title card`)
      await card(page, cdp, id)
    }
    return
  }
  await resetDemo(origin)
  await page.context().addInitScript(overlay)
  const cdp = await page.context().newCDPSession(page)
  const content = page.locator('#content')

  // The story: a business with a hunch, the cost of fraud, then Kredibel.
  await card(page, cdp, 'problem')
  await card(page, cdp, 'stat')
  await card(page, cdp, 'intro')

  // Sign in with the demo account; the welcome question; what the owner expects.
  await page.goto('/login')
  await expect(page.getByLabel('Email address')).toBeVisible()
  let scene = new Scene(page, cdp, 'signin')
  await scene.begin()
  await scene.say(0)
  await typeInto(page, page.getByLabel('Email address'), EMAIL)
  await typeInto(page, page.getByLabel(/Password/), PASSWORD)
  await press(page, page.getByRole('button', { name: 'Sign in', exact: true }))
  await scene.cut(() => expect(page.getByRole('heading', { name: /What would you like Kredibel to do first/ })).toBeVisible({ timeout: 60_000 }))
  await scene.say(1)
  await glide(page, page.getByRole('button', { name: /Keep my books/ }), 800)
  await glide(page, page.getByRole('button', { name: /Check what I expect/ }), 700)
  await scene.say(2)
  await press(page, page.getByRole('button', { name: /Check what I expect/ }), 300)
  await scene.say(3)
  await typeInto(page, page.getByLabel('Money in').first(), '820000000')
  await typeInto(page, page.getByLabel('Money out').first(), '840000000')
  await press(page, page.getByRole('button', { name: 'Add a month' }))
  const month = page.getByLabel('Month').nth(1)
  await press(page, month, 500)
  await month.fill('2026-10')
  await typeInto(page, page.getByLabel('Money in').nth(1), '1000000000')
  await typeInto(page, page.getByLabel('Money out').nth(1), '620000000')
  await glide(page, page.getByRole('button', { name: 'Save and go to my dashboard' }), 700)
  await scene.end(-0.4)
  await page.getByRole('button', { name: 'Save and go to my dashboard' }).click()

  // The dashboard against the expectations.
  await expect(page.getByRole('heading', { name: 'What you expected' })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByText('Matched by Kredibel', { exact: true }).first()).toBeVisible()
  await sleep(1500)
  scene = new Scene(page, cdp, 'dashboard')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.getByText('Money in', { exact: true }).first(), 700)
  await glide(page, content.getByText('Money out', { exact: true }).first(), 600)
  await scrollTo(page.getByRole('heading', { name: 'What you expected' }), 0.12)
  await scene.say(1)
  await glide(page, content.getByText('As expected').first(), 700)
  await sleep(900)
  await glide(page, content.getByText(/more than expected/).first(), 900)
  await scene.say(2)
  await scrollTo(page.getByRole('heading', { name: 'Sunrise Coffee Roasters', level: 1 }), 0.1)
  await glide(page, content.getByText('Matched by Kredibel', { exact: true }).first(), 800)
  await scene.end()

  // Every October bank line.
  scene = new Scene(page, cdp, 'transactions')
  await scene.begin()
  await scene.say(0)
  await press(page, page.getByRole('link', { name: 'Transactions' }).first())
  await scene.cut(async () => {
    await expect(page.getByRole('heading', { name: 'Transactions', level: 1 })).toBeVisible({ timeout: 60_000 })
    await expect(content.locator('.data-table tbody tr', { hasText: 'CASH DEPOSIT' }).first()).toBeVisible({ timeout: 60_000 })
  })
  await glide(page, content.locator('.data-table tbody tr').nth(2), 800)
  await scene.say(1)
  for (const name of ['Category', 'IFRS', 'US GAAP', 'Subledger', 'Matched to']) {
    await glide(page, content.locator('.data-table th', { hasText: name }).first(), 450)
    await sleep(350)
  }
  await scene.say(2)
  await press(page, content.locator('.data-table tbody tr', { hasText: 'CASH DEPOSIT' }).first())
  const drawer = page.getByRole('dialog')
  await scene.cut(() => expect(drawer.getByText('From its match')).toBeVisible({ timeout: 30_000 }))
  await glide(page, drawer.getByText('From its match'), 700)
  await sleep(900)
  await glide(page, drawer.locator('.tx-records a').first(), 700)
  await scene.end()

  // October's reconciliation.
  await closeDrawer(page)
  await page.goto('/months/2026-10')
  await expect(page.getByRole('heading', { name: 'October 2026' }).first()).toBeVisible({ timeout: 60_000 })
  await expect(content.locator('.data-table tbody tr', { hasText: 'Matched by Kredibel' }).first()).toBeVisible({ timeout: 60_000 })
  await sleep(1200)
  scene = new Scene(page, cdp, 'month')
  await scene.begin()
  await scene.say(0)
  await glide(page, page.getByRole('heading', { name: 'High risk this month' }), 800)
  await scene.say(1)
  await scrollTo(content.locator('.data-table').first(), 0.18)
  await glide(page, content.locator('.data-table tbody .match-chip').nth(1), 800)
  await sleep(700)
  await glide(page, content.locator('.data-table tbody .reason').nth(1), 700)
  await scene.end()

  // The risks the owner was afraid of.
  await page.goto('/risk')
  await expect(page.getByRole('heading', { name: 'Risk', level: 1 })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByText('X08').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'risk')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.locator(':is(a,button)').filter({ hasText: /^Aug\s*2026/ }).first(), 700)
  await glide(page, content.locator(':is(a,button)').filter({ hasText: /^Oct\s*2026/ }).first(), 700)
  await scene.say(1)
  const october = content.locator('tr', { hasText: 'X08' }).first()
  await scrollTo(october, 0.45)
  await glide(page, october, 900, 0.35)
  await sleep(1200)
  await glide(page, october, 900, 0.7)
  await scene.say(2)
  const font = content.locator('tr', { hasText: 'M04' }).first()
  await scrollTo(font, 0.4)
  await press(page, font.getByText('M04'))
  await scene.cut(async () => {
    const image = page.getByRole('dialog').locator('img').first()
    await expect(image).toBeVisible({ timeout: 30_000 })
    await expect.poll(() => image.evaluate((img) => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0), { timeout: 30_000 }).toBe(true)
    await sleep(600)
  })
  await scene.say(3)
  await glide(page, page.getByRole('dialog').getByRole('heading').first(), 800)
  await scene.end()

  // Late July files, and a copy of one already read.
  await closeDrawer(page)
  await page.goto('/documents')
  await expect(page.getByRole('heading', { name: 'Documents', level: 1 })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByText('statement-2026-10.pdf').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'upload')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.getByText('Choose files').first(), 700)
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
  await scene.cut(async () => {
    await expect(notice).toBeVisible({ timeout: 60_000 })
    await expect(tray.getByText('Reading').first()).toBeVisible({ timeout: 60_000 })
  })
  await glide(page, tray.locator('li').first(), 700)
  await scene.say(1)
  await glide(page, notice, 800)
  await scene.say(2)
  const readAs = (name: string) => tray.locator('li', { hasText: name }).getByText(/^Read as/)
  await scene.cut(async () => {
    await expect(readAs('inv-sales-2026-07-04')).toBeVisible({ timeout: 300_000 })
    await expect(readAs('receipt-2026-07-01')).toBeVisible({ timeout: 300_000 })
  })
  const invoiceRow = tray.locator('li', { hasText: 'inv-sales-2026-07-04' })
  await glide(page, invoiceRow.getByText(/^Read as/), 700)
  await press(page, invoiceRow.getByRole('link', { name: 'Open' }), 600)
  const total = content.locator('button', { hasText: /^Total/ }).first()
  await scene.cut(() => expect(total).toBeVisible({ timeout: 60_000 }))
  await scene.say(3)
  await press(page, total, 800)
  await sleep(700)
  await glide(page, total.getByText('On the page'), 600)
  await scene.end(1)

  // What only a person can decide.
  await page.goto('/review')
  await expect(page.getByRole('heading', { name: 'Review', level: 1 })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByText('This invoice was already uploaded').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'review')
  await scene.begin()
  await scene.say(0)
  for (const chip of ['Possible copies', 'Choose a match', 'Not paid', 'Check a value']) {
    await glide(page, content.getByRole('button', { name: new RegExp(chip) }), 450)
    await sleep(250)
  }
  await scene.say(1)
  await press(page, content.locator('.data-table tbody tr').first())
  await scene.cut(() => expect(page.getByRole('dialog')).toBeVisible({ timeout: 30_000 }))
  await glide(page, page.getByRole('dialog').getByRole('heading').first(), 800)
  await scene.end()

  // Every AI decision, every run.
  await closeDrawer(page)
  await page.goto('/labels')
  await expect(page.getByRole('heading', { name: 'Labels', level: 1 })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByRole('button', { name: /^All\s*[1-9]/ }).first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'labels')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.locator('.data-table tbody tr').nth(1), 700)
  await sleep(500)
  await glide(page, content.locator('.data-table tbody tr').nth(3), 700)
  await scene.say(1)
  await press(page, page.getByRole('link', { name: 'Runs' }).first())
  const documentRuns = content.getByRole('button', { name: /^Document\s*[1-9]/ })
  await scene.cut(() => expect(documentRuns).toBeVisible({ timeout: 60_000 }))
  await press(page, documentRuns, 450)
  await press(page, content.locator('.data-table tbody tr', { hasText: /Done/ }).first(), 600)
  await scene.cut(() => expect(page.getByRole('dialog')).toBeVisible({ timeout: 30_000 }))
  await glide(page, page.getByRole('dialog').locator('.span-row.llm').first(), 900)
  await scene.end(1)

  // Ask the books.
  await closeDrawer(page)
  await page.goto('/assistant')
  const composer = content.locator('.composer input').first()
  await expect(composer).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'assistant')
  await scene.begin()
  await scene.say(0)
  await typeInto(page, composer, 'How much money went out in October 2026?')
  await page.keyboard.press('Enter')
  await scene.cut(() => expect(content.getByText(/705,933,026/).first()).toBeVisible({ timeout: 120_000 }))
  await scene.say(1)
  await glide(page, content.getByText(/705,933,026/).first(), 800)
  await scene.end(1.5)

  // Your own books: sign in with Google, set up the business, and the free trial starts. Only with
  // VIDEO_OWNER_TOKEN; that account's own workspace is never opened (the scene ends at the welcome
  // question, which shows nothing of it).
  const ownerToken = process.env.VIDEO_OWNER_TOKEN
  if (ownerToken) {
    const own = await browser.newContext({ ...test.info().project.use, baseURL: origin })
    await own.addInitScript(overlay)
    const ownPage = await own.newPage()
    const ownCdp = await own.newCDPSession(ownPage)
    const session = await ownerSession(origin, ownerToken)
    await ownPage.goto('/login')
    const google = ownPage.getByRole('button', { name: /Google/ }).first()
    await expect(google).toBeVisible({ timeout: 60_000 })
    await sleep(1000)
    resetMouse()
    scene = new Scene(ownPage, ownCdp, 'onboarding')
    await scene.begin()
    await scene.say(0)
    await glide(ownPage, google, 900)
    await sleep(150)
    // The click's ripple only: Google's account chooser is not filmed.
    await ownPage.evaluate(({ x, y }) => window.dispatchEvent(new MouseEvent('mousedown', { clientX: x, clientY: y })), cursor())
    await sleep(500)
    await scene.cut(async () => {
      await ownPage.evaluate(([k, v]) => localStorage.setItem(k, v), [session.key, session.user])
      await ownPage.goto('/onboarding')
      await expect(ownPage.getByRole('heading', { name: 'Set up your business' })).toBeVisible({ timeout: 60_000 })
      await sleep(800)
    })
    await scene.say(1)
    await typeInto(ownPage, ownPage.getByLabel('Legal name'), 'Bandung Brew Co.')
    await press(ownPage, ownPage.getByLabel('Industry'), 500)
    await ownPage.getByLabel('Industry').selectOption({ label: 'Food and drink, cafes and restaurants' })
    await glide(ownPage, ownPage.getByLabel('Currency'), 600)
    await glide(ownPage, ownPage.getByLabel('Time zone'), 600)
    await scene.say(2)
    // The owner's own Google account, clear of the caption; the pointer on the address, not on Sign out.
    const signedIn = ownPage.getByText(/Signed in as/).first()
    await scrollTo(signedIn, 0.5)
    await glide(ownPage, signedIn, 800, 0.3)
    await sleep(600)
    await press(ownPage, ownPage.getByRole('button', { name: 'Start the free trial' }), 700)
    await scene.cut(() => expect(ownPage.getByRole('heading', { name: /What would you like Kredibel to do first/ })).toBeVisible({ timeout: 60_000 }))
    await glide(ownPage, ownPage.getByRole('button', { name: /Keep my books/ }), 800)
    await scene.end(1)
    await own.close()
  } else {
    fs.rmSync(path.join(OUT, FRAMES, 'onboarding'), { recursive: true, force: true })
  }

  await card(page, cdp, 'close')
})
