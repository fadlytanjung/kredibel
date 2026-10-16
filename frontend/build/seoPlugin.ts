import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { basename, resolve } from 'node:path'
import { loadEnv, type Plugin, type ResolvedConfig } from 'vite'
import { DEFAULT_SITE_URL, PUBLIC_PAGES } from '../src/shared/config/publicSite.ts'
import { headTags, injectHead, jsonLd, robotsTxt, sitemapXml, type SeoCopy } from '../src/shared/config/seo.ts'

/**
 * Writes each public page's head into the build (spec 020, AC-020-13): `dist/index.html` becomes the
 * landing, `dist/<route>.html` the other public pages (Firebase `cleanUrls` and the Cloud Run origin
 * serve `/pricing` from `pricing.html`), plus `dist/sitemap.xml` and the `Sitemap:` line of
 * `dist/robots.txt`. Build only, and only for the app's own `dist` (Storybook reuses this config).
 */
export function seoPlugin(): Plugin {
  let config: ResolvedConfig
  return {
    name: 'kredibel-seo',
    apply: 'build',
    configResolved(resolved) {
      config = resolved
    },
    closeBundle() {
      const outDir = resolve(config.root, config.build.outDir)
      const shellPath = resolve(outDir, 'index.html')
      if (basename(outDir) !== 'dist' || !existsSync(shellPath)) return

      const env = loadEnv(config.mode, config.envDir || config.root, 'VITE_')
      const siteUrl = env.VITE_SITE_URL || DEFAULT_SITE_URL
      const copy = JSON.parse(
        readFileSync(resolve(config.root, 'src/shared/i18n/locales/en/public.json'), 'utf-8'),
      ) as SeoCopy
      const shell = readFileSync(shellPath, 'utf-8')

      for (const page of PUBLIC_PAGES) {
        const file = page.path === '/' ? 'index.html' : `${page.path.slice(1)}.html`
        writeFileSync(resolve(outDir, file), injectHead(shell, headTags(page, copy, siteUrl), jsonLd(page, copy, siteUrl)))
      }
      writeFileSync(resolve(outDir, 'sitemap.xml'), sitemapXml(PUBLIC_PAGES, siteUrl))
      const robotsPath = resolve(outDir, 'robots.txt')
      const robots = existsSync(robotsPath) ? readFileSync(robotsPath, 'utf-8') : 'User-agent: *\nAllow: /\n'
      writeFileSync(robotsPath, robotsTxt(robots, siteUrl))
      config.logger.info(`kredibel-seo: ${PUBLIC_PAGES.length} page heads and the sitemap for ${siteUrl}`)
    },
  }
}
