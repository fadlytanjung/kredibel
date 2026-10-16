/**
 * The public site's pages for search and link previews (spec 020, AC-020-13): one list read by the
 * router (its public routes are typed against it), the build's SEO plugin and `PageMeta`. Pure data
 * and no env, so `vite.config.ts` can import it in Node.
 */
export interface PublicPage {
  path: string
  /** `meta.<meta>Title` / `meta.<meta>Description` in `public.json`. */
  meta: string
  changefreq: 'weekly' | 'monthly' | 'yearly'
  priority: number
}

export const PUBLIC_PAGES = [
  { path: '/', meta: 'home', changefreq: 'weekly', priority: 1 },
  { path: '/pricing', meta: 'pricing', changefreq: 'monthly', priority: 0.8 },
  { path: '/how-it-works', meta: 'how', changefreq: 'monthly', priority: 0.8 },
  { path: '/security', meta: 'security', changefreq: 'monthly', priority: 0.6 },
  { path: '/faq', meta: 'faq', changefreq: 'monthly', priority: 0.6 },
  { path: '/contact', meta: 'contact', changefreq: 'yearly', priority: 0.4 },
  { path: '/privacy', meta: 'privacy', changefreq: 'yearly', priority: 0.3 },
  { path: '/terms', meta: 'terms', changefreq: 'yearly', priority: 0.3 },
] as const satisfies readonly PublicPage[]

export type PublicPath = (typeof PUBLIC_PAGES)[number]['path']

/** The canonical origin when `VITE_SITE_URL` is not set (docs/16 §6.2). */
export const DEFAULT_SITE_URL = 'https://kredibel.app'

/** The 1200×630 social card (`npm run marketing:shots`). */
export const OG_IMAGE = { path: '/marketing/og.png', width: 1200, height: 630 }

export const CONTACT_EMAIL = 'hello@kredibel.app'
