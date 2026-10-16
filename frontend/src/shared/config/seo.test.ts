import { describe, expect, it } from 'vitest'
import copy from '../i18n/locales/en/public.json'
import { PUBLIC_PAGES } from './publicSite'
import { headTags, injectHead, jsonLd, pageUrl, robotsTxt, sitemapXml } from './seo'

const SITE = 'https://kredibel.app/'
const page = (path: string) => PUBLIC_PAGES.find((p) => p.path === path)!

describe('public site SEO (spec 020, AC-020-13)', () => {
  it('names every page on the canonical origin, with or without a trailing slash', () => {
    expect(pageUrl(SITE, '/')).toBe('https://kredibel.app/')
    expect(pageUrl('https://kredibel.app', '/pricing')).toBe('https://kredibel.app/pricing')
  })

  it("lists the landing and the seven public pages, each with its page's copy", () => {
    expect(PUBLIC_PAGES.map((p) => p.path)).toEqual([
      '/',
      '/pricing',
      '/how-it-works',
      '/security',
      '/faq',
      '/contact',
      '/privacy',
      '/terms',
    ])
    for (const p of PUBLIC_PAGES) {
      expect(copy.meta[`${p.meta}Title` as keyof typeof copy.meta]).toBeTruthy()
      expect(copy.meta[`${p.meta}Description` as keyof typeof copy.meta]).toBeTruthy()
    }
  })

  it('writes the head a link preview needs: title, description, canonical, Open Graph, Twitter', () => {
    const head = headTags(page('/pricing'), copy, SITE)
    expect(head).toContain(`<title data-prerendered>${copy.meta.pricingTitle}</title>`)
    expect(head).toContain('<link data-prerendered rel="canonical" href="https://kredibel.app/pricing">')
    expect(head).toContain('<meta data-prerendered property="og:url" content="https://kredibel.app/pricing">')
    expect(head).toContain('<meta data-prerendered property="og:image" content="https://kredibel.app/marketing/og.png">')
    expect(head).toContain('<meta data-prerendered name="twitter:card" content="summary_large_image">')
    expect(head).toContain('name="description"')
    // Every tag the build writes can be found again and removed by the app.
    for (const tag of head.split('\n').filter(Boolean)) expect(tag).toContain('data-prerendered')
  })

  it('escapes copy inside attributes and titles', () => {
    const head = headTags(page('/'), { ...copy, meta: { ...copy.meta, homeTitle: 'A <b> & "B"' } }, SITE)
    expect(head).toContain('<title data-prerendered>A &lt;b&gt; &amp; &quot;B&quot;</title>')
    expect(head).toContain('content="A &lt;b&gt; &amp; &quot;B&quot;"')
  })

  it('describes the product on the landing, without inventing ratings or prices', () => {
    const graph = JSON.parse(jsonLd(page('/'), copy, SITE))['@graph'] as { '@type': string }[]
    const types = graph.map((node) => node['@type'])
    expect(types).toEqual(expect.arrayContaining(['Organization', 'WebSite', 'SoftwareApplication', 'WebPage']))
    const app = graph.find((node) => node['@type'] === 'SoftwareApplication') as Record<string, unknown>
    expect(app.offers).toMatchObject({ '@type': 'Offer', price: '0' })
    expect(JSON.stringify(graph)).not.toContain('aggregateRating')
  })

  it('turns the FAQ copy into an FAQPage with every question', () => {
    const graph = JSON.parse(jsonLd(page('/faq'), copy, SITE))['@graph'] as Record<string, unknown>[]
    const faq = graph.find((node) => node['@type'] === 'FAQPage') as { mainEntity: { name: string }[] }
    const questions = Object.keys(copy.faq).filter((key) => /^q\d+$/.test(key))
    expect(faq.mainEntity.map((q) => q.name)).toEqual(questions.map((q) => copy.faq[q as keyof typeof copy.faq]))
  })

  it('keeps JSON-LD from closing its script element', () => {
    const json = jsonLd(page('/'), { ...copy, meta: { ...copy.meta, homeDescription: '</script><script>' } }, SITE)
    expect(json).not.toContain('</script>')
    expect(JSON.parse(json)).toBeTruthy()
  })

  it('lists every public page in the sitemap, absolute', () => {
    const xml = sitemapXml(PUBLIC_PAGES, SITE)
    expect(xml.match(/<loc>/g)).toHaveLength(PUBLIC_PAGES.length)
    expect(xml).toContain('<loc>https://kredibel.app/how-it-works</loc>')
    expect(xml).not.toContain('<lastmod>')
  })

  it('names the sitemap in robots.txt once', () => {
    const once = robotsTxt('User-agent: *\nAllow: /\n', SITE)
    expect(once).toContain('Sitemap: https://kredibel.app/sitemap.xml')
    expect(robotsTxt(once, SITE).match(/Sitemap:/g)).toHaveLength(1)
  })

  it("puts the page's head in place of the shell's title and description", () => {
    const shell =
      '<html><head><meta charset="UTF-8" /><title>Kredibel</title>\n<meta name="description" content="x" />\n</head><body></body></html>'
    const html = injectHead(shell, '<title data-prerendered>Plans</title>', '{"a":1}')
    expect(html.match(/<title/g)).toHaveLength(1)
    expect(html).not.toContain('content="x"')
    expect(html).toContain('<title data-prerendered>Plans</title>')
    expect(html).toContain('<script type="application/ld+json">{"a":1}</script>\n</head>')
  })

  it('places the page head early, right after the viewport, before the module preloads', () => {
    const shell =
      '<head>\n<meta name="viewport" content="width=device-width" />\n<script type="module" src="/a.js"></script>\n</head>'
    const html = injectHead(shell, '<title data-prerendered>Plans</title>', '{}')
    expect(html.indexOf('name="viewport"')).toBeLessThan(html.indexOf('<title'))
    expect(html.indexOf('<title')).toBeLessThan(html.indexOf('<script type="module"'))
  })
})
