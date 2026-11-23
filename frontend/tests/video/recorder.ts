/**
 * The video recorder shared by the demo cuts (tools/video): Chrome's screencast as JPEG frames per
 * scene, each action at its sentence (the timings narrate.py wrote), page loads cut from the scene's
 * clock, a cursor and a caption bar drawn in the page. tools/video/edit.py turns the frames into the
 * film. VIDEO_CUT names a cut other than the 3-minute demo: its narration, cards and frames live in
 * tools/video/<cut>/ and tools/video/out-<cut>/ (the 90-second cut is "featured").
 */
import { expect, type CDPSession, type Locator, type Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const CUT = process.env.VIDEO_CUT ?? ''
export const OUT = path.join(ROOT, CUT ? `tools/video/out-${CUT}` : 'tools/video/out')
const CARDS = path.join(ROOT, CUT ? `tools/video/${CUT}/cards` : 'tools/video/cards')
// VIDEO_CAPTIONS=0 records without the caption bar (a version to dub over, cut by edit.py --silent);
// VIDEO_FRAMES names the frames folder under tools/video/out, so the two recordings keep apart.
export const CAPTIONS = process.env.VIDEO_CAPTIONS !== '0'
export const FRAMES = process.env.VIDEO_FRAMES ?? 'frames'
export const PACK = path.join(ROOT, 'tools/synthetic/out/demo-aug-oct/pack')
// The same books a month earlier: July's files arrive late in the upload scene (make video makes them).
export const JULY = path.join(ROOT, 'tools/synthetic/out/demo-shift5/S1/seed-1')
export const EMAIL = process.env.DEMO_ACCOUNT_EMAIL ?? 'demo@kredibel.app'
export const PASSWORD = process.env.DEMO_ACCOUNT_PASSWORD ?? 'Kredibel-Demo-2026'

interface Sentence {
  text: string
  start: number
  end: number
}
export interface SceneTiming {
  id: string
  kind: 'card' | 'app' | 'camera'
  duration: number
  sentences: Sentence[]
}
export const TIMINGS: SceneTiming[] = JSON.parse(fs.readFileSync(path.join(OUT, 'timings.json'), 'utf8')).scenes

export const now = () => Date.now() / 1000
export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

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

export async function idToken(origin: string): Promise<string> {
  const res = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${webApiKey()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Referer: `${origin}/` },
    body: JSON.stringify({ email: EMAIL, password: PASSWORD, returnSecureToken: true }),
  })
  const body = (await res.json()) as { idToken?: string }
  if (!body.idToken) throw new Error(`demo sign-in failed (${res.status})`)
  return body.idToken
}

/** A Firebase session for the owner's own Google account (VIDEO_OWNER_TOKEN, a custom token for that
 * user from scripts/custom_token.py), in the form Firebase keeps it: the onboarding scene starts
 * signed in instead of going through Google's account chooser. */
export async function ownerSession(origin: string, customToken: string): Promise<{ key: string; user: string }> {
  const key = webApiKey()
  const call = async (method: string, body: object) => {
    const res = await fetch(`https://identitytoolkit.googleapis.com/v1/accounts:${method}?key=${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Referer: `${origin}/` },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`owner sign-in failed (${method} ${res.status})`)
    return res.json()
  }
  const session = (await call('signInWithCustomToken', { token: customToken, returnSecureToken: true })) as {
    idToken: string
    refreshToken: string
    expiresIn: string
  }
  const found = (await call('lookup', { idToken: session.idToken })) as {
    users: {
      localId: string
      email?: string
      emailVerified?: boolean
      displayName?: string
      photoUrl?: string
      createdAt?: string
      lastLoginAt?: string
      providerUserInfo?: { providerId: string; rawId: string; email?: string; displayName?: string; photoUrl?: string }[]
    }[]
  }
  const u = found.users[0]
  const user = {
    uid: u.localId,
    email: u.email ?? null,
    emailVerified: Boolean(u.emailVerified),
    displayName: u.displayName ?? null,
    photoURL: u.photoUrl ?? null,
    isAnonymous: false,
    providerData: (u.providerUserInfo ?? []).map((p) => ({
      providerId: p.providerId,
      uid: p.rawId,
      email: p.email ?? null,
      displayName: p.displayName ?? null,
      photoURL: p.photoUrl ?? null,
      phoneNumber: null,
    })),
    stsTokenManager: {
      refreshToken: session.refreshToken,
      accessToken: session.idToken,
      expirationTime: Date.now() + Number(session.expiresIn) * 1000,
    },
    createdAt: u.createdAt,
    lastLoginAt: u.lastLoginAt,
    apiKey: key,
    appName: '[DEFAULT]',
  }
  return { key: `firebase:authUser:${key}:[DEFAULT]`, user: JSON.stringify(user) }
}

/** A fresh copy of the demo company (no goal yet, so the welcome question shows) with the tour seen. */
export async function resetDemo(origin: string) {
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
export function overlay() {
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

/** The cursor starts again from the middle (a new browser context). */
export function resetMouse() {
  mouse = { x: 960, y: 540 }
}

/** Where the cursor is now. */
export function cursor() {
  return { ...mouse }
}

/** Glides the cursor to the element's centre (or an offset in it), eased, in about `ms`. */
export async function glide(page: Page, target: Locator | { x: number; y: number }, ms = 650, dx = 0.5, dy = 0.5) {
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

export async function press(page: Page, target: Locator, ms = 650) {
  await glide(page, target, ms)
  await sleep(120)
  await page.mouse.down()
  await sleep(60)
  await page.mouse.up()
}

export async function typeInto(page: Page, field: Locator, text: string) {
  await press(page, field, 500)
  await field.pressSequentially(text, { delay: 45 })
}

/** Scrolls smoothly so the element sits about `at` of the way down the window. */
export async function scrollTo(target: Locator, at = 0.25) {
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
export async function closeDrawer(page: Page) {
  await page.keyboard.press('Escape')
  await sleep(400)
  const behind = page.locator('.drawer-behind')
  if (await behind.count()) await behind.first().click({ force: true }).catch(() => undefined)
  await sleep(300)
}

/** One scene: its frames, its virtual clock (real time less the cut loading), its sentences. */
export class Scene {
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
    this.dir = path.join(OUT, FRAMES, id)
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
    if (this.timing.kind !== 'app') {
      await this.page.evaluate((step) => (document.body.dataset.step = String(step)), i)
    } else {
      await this.setCaption(s.text)
    }
  }

  private async setCaption(text: string) {
    this.caption = text
    if (!CAPTIONS) return
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

export async function card(page: Page, cdp: CDPSession, id: string) {
  await page.goto(`file://${path.join(CARDS, `${id}.html`)}`)
  await page.evaluate(() => document.fonts.ready)
  await sleep(400)
  const scene = new Scene(page, cdp, id)
  await scene.begin()
  const timing = TIMINGS.find((t) => t.id === id)!
  for (let i = 0; i < timing.sentences.length; i += 1) await scene.say(i)
  await scene.end()
}
