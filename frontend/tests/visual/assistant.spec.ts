/**
 * Finance Assistant parity with its mocks (spec 019, T019-02, AC-019-2, AC-019-4; spec 011,
 * AC-011-11): the welcome state, a conversation, the history rail or drawer, the composer.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)

// Synthetic threads, messages and preferences (docs/18), the same as the mocks' history rail.
const THREADS = [
  { threadId: 'th_01', title: 'How much did we pay Green Valley Farms in March?', scope: 'WORKSPACE', createdAt: '2026-07-02T09:00:00Z', lastMessageAt: '2026-07-02T09:05:00Z' },
  { threadId: 'th_02', title: 'Why is March critical?', scope: 'WORKSPACE', createdAt: '2026-07-02T08:00:00Z', lastMessageAt: '2026-07-02T08:02:00Z' },
  { threadId: 'th_03', title: 'Show my profit and loss for 2026-03', scope: 'WORKSPACE', createdAt: '2026-07-02T07:00:00Z', lastMessageAt: '2026-07-02T07:01:00Z' },
  { threadId: 'th_04', title: 'Which invoices are still unpaid?', scope: 'WORKSPACE', createdAt: '2026-07-01T10:00:00Z', lastMessageAt: '2026-07-01T10:01:00Z' },
  { threadId: 'th_05', title: 'Where did the money go in Q2?', scope: 'WORKSPACE', createdAt: '2026-06-28T10:00:00Z', lastMessageAt: '2026-06-28T10:01:00Z' },
]
const MESSAGES = [
  { messageId: 'msg_01', role: 'user', question: 'How much did we pay Green Valley Farms in March?', createdAt: '2026-07-02T09:00:00Z' },
  {
    messageId: 'msg_02',
    role: 'assistant',
    createdAt: '2026-07-02T09:00:05Z',
    answer: {
      parts: [{ type: 'text', text: 'You paid Green Valley Farms IDR 56,050,000 in March, in 3 transfers [[match:mat_mar_gvf]]. All three went to their usual account and each one matches an invoice.' }],
      citations: [{ ref: 'match:mat_mar_gvf', label: '3 bank lines' }],
      grounding: { verdict: 'AGREED', citations: ['match:mat_mar_gvf'] },
      toolsUsed: ['list_bank_lines'],
    },
  },
]
const MEMORIES = [
  { memoryId: 'mem_01', fact: 'Show amounts in millions', updatedAt: '2026-07-01T10:00:00Z' },
  { memoryId: 'mem_02', fact: 'ACB ••5577 is the payroll account', updatedAt: '2026-07-01T10:00:00Z' },
  { memoryId: 'mem_03', fact: 'The financial year starts in January', updatedAt: '2026-07-01T10:00:00Z' },
]

async function serve(page: Page, { threads = THREADS, messages = MESSAGES } = {}) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/assistant/threads') return route.fulfill({ json: { items: threads, nextCursor: null } })
    if (/\/api\/assistant\/threads\/th_\d+\/messages$/.test(path)) return route.fulfill({ json: { items: messages, nextCursor: null } })
    if (path === '/api/assistant/memories') return route.fulfill({ json: { items: MEMORIES } })
    return route.fulfill({ json: { items: [] } })
  })
}

/** The screen's outline: headings, the prompt cards, the suggested questions and the composer. */
async function outline(page: Page) {
  return {
    headings: (await page.locator('#content h1, #content h2').allTextContents()).map((s) => s.trim()),
    prompts: (await page.locator('#content .assistant-prompt-card strong').allTextContents()).map((s) => s.trim()),
    suggested: (await page.locator('#content .suggested a').allTextContents()).map((s) => s.trim()),
    composer: await page.locator('#content .composer input').getAttribute('placeholder'),
    threads: (await page.locator('#content .assistant-sidebar .assistant-thread-title').allTextContents()).map((s) => s.trim()),
  }
}

async function axeClean(page: Page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
}

test('AC-019-2: an empty thread shows the welcome prompts like the mock', async ({ page }) => {
  await serve(page, { messages: [] })
  await page.goto('/preview/assistant')
  await expect(page.getByText('How can I help with your books today?')).toBeVisible()
  await expect(page).toHaveScreenshot('assistant-welcome.png', { fullPage: true })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(pathToFileURL(resolve('../design/mocks/assistant-welcome.html')).href)
  expect(await outline(page)).toEqual(implementation)
})

test('AC-019-2: a conversation shows grounded answers beside the history', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/assistant/th_01')
  await expect(page.getByText('Every number checked against your books')).toBeVisible()
  await expect(page).toHaveScreenshot('assistant-conversation.png', { fullPage: true })
  await axeClean(page)
})

test('AC-019-2: phones open the history in a drawer; the rail returns on wide screens', async ({ page }, testInfo) => {
  await serve(page, { messages: [] })
  await page.goto('/preview/assistant')
  await expect(page.getByText('How can I help with your books today?')).toBeVisible()
  const history = page.getByRole('button', { name: 'Chat history' })
  const rail = page.getByRole('complementary', { name: 'Recent conversations' })
  if (testInfo.project.name === 'desktop-1440') {
    await expect(rail).toBeVisible()
    await expect(history).toBeHidden()
    return
  }
  await expect(rail).toBeHidden()
  await history.click()
  const drawer = page.getByRole('dialog', { name: 'Chat history' })
  await expect(drawer.getByText('Earlier questions')).toBeVisible()
  await expect(drawer.getByText('Why is March critical?')).toBeVisible()
  await expect(drawer).toHaveScreenshot('assistant-history.png')
  await drawer.getByRole('button', { name: 'Close history' }).click()
  await expect(drawer).toHaveCount(0)
})

test('AC-019-4: the composer works from the keyboard at 360 and 1600 px', async ({ page }) => {
  await serve(page, { messages: [] })
  await page.goto('/preview/assistant')
  await expect(page.getByText('How can I help with your books today?')).toBeVisible()
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const input = page.getByRole('textbox', { name: 'Ask about your books' })
    await input.focus()
    await input.fill('Which invoices are still unpaid?')
    const send = page.getByRole('button', { name: 'Send' })
    await expect(send).toBeEnabled()
    const box = await send.boundingBox()
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(40)
    await input.fill('')
    await expect(send).toBeDisabled()
  }
})
