import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PageMeta } from './PageMeta'

const head = () => document.head

afterEach(() => {
  // Unmount first: React removes the tags it hoisted, then the build's leftovers go.
  cleanup()
  head().innerHTML = ''
})

describe('PageMeta (spec 020, AC-020-13)', () => {
  it('names the page on the canonical origin, with its Open Graph and Twitter card', () => {
    render(<PageMeta title="Plans — Kredibel" description="Start free." path="/pricing" />)
    expect(document.title).toBe('Plans — Kredibel')
    expect(head().querySelector('link[rel="canonical"]')).toHaveAttribute('href', 'https://kredibel.app/pricing')
    expect(head().querySelector('meta[property="og:url"]')).toHaveAttribute('content', 'https://kredibel.app/pricing')
    expect(head().querySelector('meta[property="og:image"]')).toHaveAttribute(
      'content',
      'https://kredibel.app/marketing/og.png',
    )
    expect(head().querySelector('meta[name="twitter:card"]')).toHaveAttribute('content', 'summary_large_image')
    expect(head().querySelector('meta[name="robots"]')).toBeNull()
  })

  it('keeps a page out of the index when asked', () => {
    render(<PageMeta title="Page not found" noindex />)
    expect(head().querySelector('meta[name="robots"]')).toHaveAttribute('content', 'noindex')
    expect(head().querySelector('link[rel="canonical"]')).toBeNull()
  })

  it("replaces the build's head instead of doubling it", () => {
    head().innerHTML =
      '<title data-prerendered>Kredibel — every number has a source</title>' +
      '<link data-prerendered rel="canonical" href="https://kredibel.app/">' +
      '<meta data-prerendered property="og:url" content="https://kredibel.app/">'
    render(<PageMeta title="Questions — Kredibel" path="/faq" />)
    expect(head().querySelectorAll('[data-prerendered]')).toHaveLength(0)
    expect(head().querySelectorAll('title')).toHaveLength(1)
    expect(head().querySelectorAll('link[rel="canonical"]')).toHaveLength(1)
    expect(head().querySelector('link[rel="canonical"]')).toHaveAttribute('href', 'https://kredibel.app/faq')
  })
})
