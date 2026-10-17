/**
 * Records the demo video's scenes (tools/video/narration.json) on production with the public demo
 * account (synthetic data, docs/25). Each scene is captured with Chrome's screencast as JPEG frames;
 * actions wait for their sentence (tools/video/out/timings.json from narrate.py), and the time a page
 * takes to load is cut from the scene's timeline. tools/video/edit.py turns the frames into the film.
 *
 * Run: make video (narrate, record, edit). Not part of `make check`.
 */
import { expect, type CDPSession, type Locator, type Page, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const OUT = path.join(ROOT, 'tools/video/out')
const CARDS = path.join(ROOT, 'tools/video/cards')
const PACK = path.join(ROOT, 'tools/synthetic/out/demo-aug-oct/pack')
const EMAIL = process.env.DEMO_ACCOUNT_EMAIL ?? 'demo@kredibel.app'
const PASSWORD = process.env.DEMO_ACCOUNT_PASSWORD ?? 'Kredibel-Demo-2026'

interface Sentence {
  text: string
  start: number
  end: number
}
interface SceneTiming {
  id: string
  kind: 'card' | 'app'
  duration: number
  sentences: Sentence[]
}
const TIMINGS: SceneTiming[] = JSON.parse(fs.readFileSync(path.join(OUT, 'timings.json'), 'utf8')).scenes

const now = () => Date.now() / 1000
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/** The public Firebase web API key, from the environment or the env files (never printed). */
function webApiKey(): string {
  if (process.env.VITE_FIREBASE_API_KEY) return process.env.VITE_FIREBASE_API_KEY
  for (const name of ['frontend/.env.production', 'frontend/.env', '.env.production', '.env']) {
    const file = path.join(ROOT, name)
    if (!fs.existsSync(file)) continue
    const line = fs.readFileSync(file, 'utf8').split('\n').find((l) => l.startsWith('VITE_FIREBASE_API_KEY='))
    if (line) return line.slice('VITE_FIREBASE_API_KEY='.length).replace(/"/g, '').trim()
  }
  throw new Error('Set VITE_FIREBASE_API_KEY (the public web API key)')
}

async function idToken(origin: string): Promise<string> {
  const res = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${webApiKey()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Referer: `${origin}/` },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD, returnSecureToken: true }),
  })
  const body = (await res.json()) as { idToken?: string }
  if (!body.idToken) throw new Error(`demo sign-in failed (${res.status})`)
  return body.idToken
}

/** A fresh copy of the demo company (no goal yet, so the welcome question shows) with the tour seen. */
async function resetDemo(origin: string) {
  const reset = await fetch(`${origin}/api/workspaces/demo/reset`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${await idToken(origin)}` },
  })
  expect(reset.status).toBe(200)
  const fresh = await idToken(origin) // the new workspace's claims
  const tour = await fetch(`${origin}/api/me/tour`, { method: 'POST', headers: { Authorization: `Bearer ${fresh}` } })
  expect(tour.ok).toBe(true)
}

/** A visible cursor with a click ripple, and the caption bar, drawn in every page. */
function overlay() {
  const install = () => {
    if (location.protocol === 'file:' || document.getElementById('__demo_cursor') || !document.body) return
    const style = document.createElement('style')
    style.textContent = `
      #__demo_cursor{position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px)}
      #__demo_cursor svg{filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
      .__demo_ripple{position:fixed;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;z-index:2147483646;pointer-events:none;
        border:3px solid rgba(14,90,71,.85);animation:__demo_ripple .55s ease-out forwards}
      @keyframes __demo_ripple{from{transform:scale(.3);opacity:1}to{transform:scale(1.5);opacity:0}}
      #__demo_caption{position:fixed;left:50%;bottom:44px;transform:translateX(-50%);max-width:1380px;z-index:2147483645;pointer-events:none;
        padding:16px 28px;border-radius:14px;background:rgba(22,33,43,.88);color:#fff;font:500 29px/1.35 system-ui,-apple-system,"Segoe UI",sans-serif;
        text-align:center;opacity:0;transition:opacity .25s ease}
      #__demo_caption.on{opacity:1}`
    document.head.appendChild(style)
    const cursor = document.createElement('div')
    cursor.id = '__demo_cursor'
    cursor.innerHTML =
      '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 11.2-6.3 1 3.7 7.3-2.9 1.5-3.7-7.4L4 20z" fill="#16212B" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>'
    const caption = document.createElement('div')
    caption.id = '__demo_caption'
    document.body.append(cursor, caption)
    window.addEventListener('mousemove', (e) => (cursor.style.transform = `translate(${e.clientX - 4}px,${e.clientY - 2}px)`), true)
    window.addEventListener(
      'mousedown',
      (e) => {
        const ring = document.createElement('div')
        ring.className = '__demo_ripple'
        ring.style.left = `${e.clientX}px`
        ring.style.top = `${e.clientY}px`
        document.body.appendChild(ring)
        setTimeout(() => ring.remove(), 600)
      },
      true,
    )
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install)
  else install()
  new MutationObserver(install).observe(document.documentElement, { childList: true, subtree: false })
}

let mouse = { x: 960, y: 540 }

/** Glides the cursor to the element's centre (or an offset in it), eased, in about `ms`. */
async function glide(page: Page, target: Locator | { x: number; y: number }, ms = 650, dx = 0.5, dy = 0.5) {
  let x: number
  let y: number
  if ('x' in target) ({ x, y } = target)
  else {
    await target.scrollIntoViewIfNeeded()
    const box = await target.boundingBox()
    if (!box) throw new Error('nothing to point at')
    x = box.x + box.width * dx
    y = box.y + box.height * dy
  }
  const from = { ...mouse }
  const steps = Math.max(8, Math.round(ms / 16))
  for (let i = 1; i <= steps; i += 1) {
    const t = i / steps
    const e = t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2
    await page.mouse.move(from.x + (x - from.x) * e, from.y + (y - from.y) * e)
    await sleep(16)
  }
  mouse = { x, y }
}

async function press(page: Page, target: Locator, ms = 650) {
  await glide(page, target, ms)
  await sleep(120)
  await page.mouse.down()
  await sleep(60)
  await page.mouse.up()
}

async function typeInto(page: Page, field: Locator, text: string) {
  await press(page, field, 500)
  await field.pressSequentially(text, { delay: 45 })
}

/** Scrolls smoothly so the element sits about `at` of the way down the window. */
async function scrollTo(target: Locator, at = 0.25) {
  await target.evaluate((el, ratio) => {
    let box: HTMLElement | null = el.parentElement
    while (box && !(box.scrollHeight > box.clientHeight && /(auto|scroll)/.test(getComputedStyle(box).overflowY))) box = box.parentElement
    const scroller = box ?? (document.scrollingElement as HTMLElement)
    const top = scroller.scrollTop + el.getBoundingClientRect().top - (box ? box.getBoundingClientRect().top : 0) - window.innerHeight * ratio
    scroller.scrollTo({ top, behavior: 'smooth' })
  }, at)
  await sleep(1000)
}

/** Closes the open drawer: Esc, or a click beside it. */
async function closeDrawer(page: Page) {
  await page.keyboard.press('Escape')
  await sleep(400)
  const behind = page.locator('.drawer-behind')
  if (await behind.count()) await behind.first().click({ force: true }).catch(() => undefined)
  await sleep(300)
}

/** One scene: its frames, its virtual clock (real time less the cut loading), its sentences. */
class Scene {
  private frames: { f: string; ts: number }[] = []
  private cuts: [number, number][] = []
  private start = 0
  private seq = 0
  private caption = ''
  private readonly dir: string
  private readonly timing: SceneTiming

  constructor(
    private readonly page: Page,
    private readonly cdp: CDPSession,
    id: string,
  ) {
    const timing = TIMINGS.find((t) => t.id === id)
    if (!timing) throw new Error(`no timing for ${id}`)
    this.timing = timing
    this.dir = path.join(OUT, 'frames', id)
    fs.rmSync(this.dir, { recursive: true, force: true })
    fs.mkdirSync(this.dir, { recursive: true })
  }

  private onFrame = (frame: { data: string; sessionId: number }) => {
    const f = `${String(this.seq++).padStart(5, '0')}.jpg`
    fs.writeFileSync(path.join(this.dir, f), Buffer.from(frame.data, 'base64'))
    this.frames.push({ f, ts: now() })
    void this.cdp.send('Page.screencastFrameAck', { sessionId: frame.sessionId }).catch(() => undefined)
  }

  async begin() {
    await this.page.mouse.move(mouse.x, mouse.y)
    this.cdp.on('Page.screencastFrame', this.onFrame)
    await this.cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 })
    this.start = now()
  }

  /** Seconds of the scene so far, the cut loading left out. */
  vnow() {
    return now() - this.start - this.cuts.reduce((sum, [a, b]) => sum + (b - a), 0)
  }

  async at(t: number) {
    while (this.vnow() < t) await sleep(20)
  }

  /** Runs `work` (a page loading, a model answering) with its time cut from the film. */
  async cut<T>(work: () => Promise<T>): Promise<T> {
    const a = now()
    const result = await work()
    await sleep(250)
    this.cuts.push([a, now()])
    if (this.caption) await this.setCaption(this.caption)
    return result
  }

  /** Waits for sentence i, then shows it (app scenes) or reveals step i (cards). */
  async say(i: number) {
    const s = this.timing.sentences[i]
    await this.at(s.start)
    if (this.timing.kind === 'card') {
      await this.page.evaluate((step) => (document.body.dataset.step = String(step)), i)
    } else {
      await this.setCaption(s.text)
    }
  }

  private async setCaption(text: string) {
    this.caption = text
    await this.page
      .evaluate((t) => {
        const el = document.getElementById('__demo_caption')
        if (!el) return
        el.textContent = t
        el.classList.toggle('on', Boolean(t))
      }, text)
      .catch(() => undefined)
  }

  async end(hold = 0) {
    await this.at(this.timing.duration + hold)
    await this.setCaption('')
    await sleep(150)
    await this.cdp.send('Page.stopScreencast')
    this.cdp.off('Page.screencastFrame', this.onFrame)
    const manifest = { id: this.timing.id, start: this.start, end: now(), cuts: this.cuts, frames: this.frames }
    fs.writeFileSync(path.join(this.dir, 'manifest.json'), JSON.stringify(manifest))
  }
}

async function card(page: Page, cdp: CDPSession, id: string) {
  await page.goto(`file://${path.join(CARDS, `${id}.html`)}`)
  await page.evaluate(() => document.fonts.ready)
  await sleep(400)
  const scene = new Scene(page, cdp, id)
  await scene.begin()
  const timing = TIMINGS.find((t) => t.id === id)!
  for (let i = 0; i < timing.sentences.length; i += 1) await scene.say(i)
  await scene.end()
}

test('record the demo video', async ({ page, baseURL }) => {
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
  await typeInto(page, page.getByLabel('Money in').first(), '130000000')
  await typeInto(page, page.getByLabel('Money out').first(), '115000000')
  await press(page, page.getByRole('button', { name: 'Add a month' }))
  const month = page.getByLabel('Month').nth(1)
  await press(page, month, 500)
  await month.fill('2026-10')
  await typeInto(page, page.getByLabel('Money in').nth(1), '160000000')
  await typeInto(page, page.getByLabel('Money out').nth(1), '120000000')
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

  // The same file twice.
  await closeDrawer(page)
  await page.goto('/documents')
  await expect(page.getByRole('heading', { name: 'Documents', level: 1 })).toBeVisible({ timeout: 60_000 })
  await expect(content.getByText('statement-2026-10.pdf').first()).toBeVisible({ timeout: 60_000 })
  await sleep(1000)
  scene = new Scene(page, cdp, 'upload')
  await scene.begin()
  await scene.say(0)
  await glide(page, content.getByText('Choose files').first(), 700)
  await page.locator('input[type="file"]').first().setInputFiles(path.join(PACK, 'statement-2026-10.pdf'))
  const notice = content.getByText(/Not read again and not counted/).first()
  await scene.cut(() => expect(notice).toBeVisible({ timeout: 60_000 }))
  await glide(page, notice, 700)
  await scene.end(2.5)

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
  await scene.cut(() => expect(content.getByText(/152,306,418/).first()).toBeVisible({ timeout: 120_000 }))
  await scene.say(1)
  await glide(page, content.getByText(/152,306,418/).first(), 800)
  await scene.end(3)

  await card(page, cdp, 'close')
})
