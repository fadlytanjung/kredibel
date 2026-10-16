import { useEffect } from 'react'
import { DEFAULT_SITE_URL, OG_IMAGE } from '../config/publicSite'
import { pageUrl } from '../config/seo'

/**
 * A public page's head (spec 020, AC-020-13): title, description, canonical URL, Open Graph and
 * Twitter card, or `noindex`. React 19 hoists these into <head>, so no dependency is needed. The build
 * writes the same tags into each route's HTML for crawlers and link previews (`frontend/build/
 * seoPlugin.ts`, marked `data-prerendered`); on mount they are removed so the head never doubles.
 */
export interface PageMetaProps {
  title: string
  description?: string
  /** The page's public path; gives the canonical URL and `og:url`. */
  path?: string
  /** Keep this page out of search results (the 404 page). */
  noindex?: boolean
  ogImage?: string
}

const SITE_URL = import.meta.env.VITE_SITE_URL || DEFAULT_SITE_URL

export function PageMeta({ title, description, path, noindex = false, ogImage }: PageMetaProps) {
  useEffect(() => {
    document.head.querySelectorAll('[data-prerendered]').forEach((node) => node.remove())
  }, [])

  const url = path ? pageUrl(SITE_URL, path) : undefined
  const image = ogImage ?? pageUrl(SITE_URL, OG_IMAGE.path)
  return (
    <>
      <title>{title}</title>
      {description && <meta name="description" content={description} />}
      {noindex && <meta name="robots" content="noindex" />}
      {url && <link rel="canonical" href={url} />}
      <meta property="og:type" content="website" />
      <meta property="og:title" content={title} />
      {description && <meta property="og:description" content={description} />}
      {url && <meta property="og:url" content={url} />}
      <meta property="og:image" content={image} />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      {description && <meta name="twitter:description" content={description} />}
      <meta name="twitter:image" content={image} />
    </>
  )
}
