import { useEffect, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { PublicFooter } from './PublicFooter'
import { PublicHeader } from './PublicHeader'

/**
 * The public page frame (spec 018; docs/12 §12): the floating header, the page and the footer. Every
 * public page opens on an ink hero, so the header always sits on ink. A new page starts at the top
 * (unless the link points into the page).
 */
export interface PublicShellProps {
  children: ReactNode
}

export function PublicShell({ children }: PublicShellProps) {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (!hash && document.scrollingElement) document.scrollingElement.scrollTop = 0
  }, [pathname, hash])

  return (
    <div className="viewport">
      <div className="site">
        <PublicHeader />
        <main className="site-main" id="content">
          {children}
        </main>
        <PublicFooter />
      </div>
    </div>
  )
}
