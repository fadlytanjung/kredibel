/**
 * Document title and description for a public page (spec 018). React 19 hoists <title> and <meta>
 * rendered anywhere in the tree into <head>, so no dependency is needed.
 */
export interface PageMetaProps {
  title: string
  description?: string
  ogImage?: string
}

export function PageMeta({ title, description, ogImage }: PageMetaProps) {
  return (
    <>
      <title>{title}</title>
      {description && <meta name="description" content={description} />}
      <meta property="og:title" content={title} />
      {description && <meta property="og:description" content={description} />}
      <meta property="og:type" content="website" />
      {ogImage && <meta property="og:image" content={ogImage} />}
    </>
  )
}
