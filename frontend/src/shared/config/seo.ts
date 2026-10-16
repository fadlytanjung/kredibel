import { CONTACT_EMAIL, OG_IMAGE, type PublicPage } from './publicSite.ts'

/**
 * Builders for the public site's head, structured data, sitemap and robots (spec 020, AC-020-13).
 * Pure strings: the build writes them into each route's HTML (`frontend/build/seoPlugin.ts`) and the
 * app reuses `pageUrl`. Every head tag carries `data-prerendered` so `PageMeta` can replace it.
 */

/** The `public.json` copy these builders read. */
export interface SeoCopy {
  meta: Record<string, string>
  faq: Record<string, string>
  landing: { title: string }
}

export function pageUrl(siteUrl: string, path: string): string {
  return `${siteUrl.replace(/\/+$/, '')}${path}`
}

const escapeHtml = (value: string) =>
  value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

const tag = (name: string, attrs: Record<string, string>) =>
  `<${name} data-prerendered ${Object.entries(attrs)
    .map(([key, value]) => `${key}="${escapeHtml(value)}"`)
    .join(' ')}>`

/** The page's own head: title, description, canonical, Open Graph and Twitter card. */
export function headTags(page: PublicPage, copy: SeoCopy, siteUrl: string): string {
  const title = copy.meta[`${page.meta}Title`]
  const description = copy.meta[`${page.meta}Description`]
  const url = pageUrl(siteUrl, page.path)
  const image = pageUrl(siteUrl, OG_IMAGE.path)
  return [
    `<title data-prerendered>${escapeHtml(title)}</title>`,
    tag('meta', { name: 'description', content: description }),
    tag('link', { rel: 'canonical', href: url }),
    tag('meta', { property: 'og:type', content: 'website' }),
    tag('meta', { property: 'og:locale', content: 'en' }),
    tag('meta', { property: 'og:title', content: title }),
    tag('meta', { property: 'og:description', content: description }),
    tag('meta', { property: 'og:url', content: url }),
    tag('meta', { property: 'og:image', content: image }),
    tag('meta', { property: 'og:image:width', content: String(OG_IMAGE.width) }),
    tag('meta', { property: 'og:image:height', content: String(OG_IMAGE.height) }),
    tag('meta', { property: 'og:image:alt', content: copy.landing.title }),
    tag('meta', { name: 'twitter:card', content: 'summary_large_image' }),
    tag('meta', { name: 'twitter:title', content: title }),
    tag('meta', { name: 'twitter:description', content: description }),
    tag('meta', { name: 'twitter:image', content: image }),
  ].join('\n')
}

/**
 * Structured data, as one JSON-LD graph: the organization, the site and the product on the landing,
 * the questions on the FAQ, and the page itself everywhere. Only facts the pages state: no ratings,
 * no prices beyond the free trial. `<` is escaped so the JSON can never close its script element.
 */
export function jsonLd(page: PublicPage, copy: SeoCopy, siteUrl: string): string {
  const site = pageUrl(siteUrl, '/')
  const url = pageUrl(siteUrl, page.path)
  const organization = { '@id': `${site}#organization` }
  const website = { '@id': `${site}#website` }
  const graph: Record<string, unknown>[] = [
    {
      '@type': 'WebPage',
      '@id': `${url}#webpage`,
      url,
      name: copy.meta[`${page.meta}Title`],
      description: copy.meta[`${page.meta}Description`],
      inLanguage: 'en',
      isPartOf: website,
    },
  ]
  if (page.path === '/') {
    graph.push(
      {
        '@type': 'Organization',
        ...organization,
        name: 'Kredibel',
        url: site,
        logo: pageUrl(siteUrl, '/brand/kredibel-mark.svg'),
        email: CONTACT_EMAIL,
      },
      { '@type': 'WebSite', ...website, name: 'Kredibel', url: site, inLanguage: 'en', publisher: organization },
      {
        '@type': 'SoftwareApplication',
        name: 'Kredibel',
        url: site,
        description: copy.meta.homeDescription,
        applicationCategory: 'FinanceApplication',
        operatingSystem: 'Web',
        publisher: organization,
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD', description: copy.meta.pricingDescription },
      },
    )
  }
  if (page.path === '/faq') {
    const questions = Object.keys(copy.faq).filter((key) => /^q\d+$/.test(key))
    graph.push({
      '@type': 'FAQPage',
      '@id': `${url}#faq`,
      mainEntity: questions.map((q) => ({
        '@type': 'Question',
        name: copy.faq[q],
        acceptedAnswer: { '@type': 'Answer', text: copy.faq[`a${q.slice(1)}`] },
      })),
    })
  }
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }).replace(/</g, '\\u003c')
}

export function sitemapXml(pages: readonly PublicPage[], siteUrl: string): string {
  const urls = pages
    .map(
      (page) =>
        `  <url>\n    <loc>${escapeHtml(pageUrl(siteUrl, page.path))}</loc>\n` +
        `    <changefreq>${page.changefreq}</changefreq>\n    <priority>${page.priority.toFixed(1)}</priority>\n  </url>`,
    )
    .join('\n')
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`
}

export function robotsTxt(robots: string, siteUrl: string): string {
  const withoutSitemap = robots.replace(/^Sitemap:.*\n?/gm, '').replace(/\s*$/, '\n')
  return `${withoutSitemap}\nSitemap: ${pageUrl(siteUrl, '/sitemap.xml')}\n`
}

/**
 * The shell with the page's head in place of its own title and description: the tags go right after
 * the viewport meta (early in the head, before the module preloads), the JSON-LD at its end.
 */
export function injectHead(html: string, head: string, structuredData: string): string {
  const shell = html
    .replace(/[ \t]*<title>[\s\S]*?<\/title>\s*\n?/, '')
    .replace(/[ \t]*<meta name="description"[^>]*>\s*\n?/, '')
  const viewport = shell.match(/<meta name="viewport"[^>]*>\n?/)
  const withHead = viewport
    ? shell.replace(viewport[0], `${viewport[0].trimEnd()}\n${head}\n`)
    : shell.replace('</head>', `${head}\n</head>`)
  return withHead.replace('</head>', `<script type="application/ld+json">${structuredData}</script>\n</head>`)
}
