import { useMotionValueEvent, useScroll } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { useScrollProgress } from '../shared/lib/useScrollProgress'
import { Icon } from '../shared/ui'
import { PUBLIC_NAV } from './publicNav'

/**
 * The public site header (spec 018, AC-018-6, 8, 9; docs/12 §12): a floating pill over every page's
 * ink hero that condenses into glass once the page scrolls, with a double-rule reading-progress line.
 * Below 940 px the links move into a menu sheet (Escape or a link closes it).
 */
export function PublicHeader() {
  const { t } = useTranslation('public')
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [condensed, setCondensed] = useState(false)
  const ref = useRef<HTMLElement>(null)
  const { scrollY } = useScroll()

  useScrollProgress(ref, { page: true })
  useMotionValueEvent(scrollY, 'change', (y) => setCondensed(y > 24))

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const close = () => setOpen(false)

  return (
    <header ref={ref} className="pub-header" data-condensed={condensed} data-menu={open ? 'open' : 'closed'}>
      <div className="pub-header-bar">
        <Link className="pub-lockup" to="/" aria-label={t('nav.home')}>
          <img src="/brand/kredibel-logo-on-dark.svg" alt="" />
        </Link>
        <nav className="pub-nav" aria-label={t('nav.menu')}>
          {PUBLIC_NAV.map((item) => (
            <NavLink key={item.key} to={item.to}>
              {t(`nav.${item.key}`)}
            </NavLink>
          ))}
        </nav>
        <div className="pub-header-actions">
          {user ? (
            <Link className="button button-accent pub-cta" to="/dashboard">
              {t('nav.goToApp')}
            </Link>
          ) : (
            <>
              <Link className="button pub-ghost pub-signin" to="/login">
                {t('nav.signIn')}
              </Link>
              <Link className="button button-accent pub-cta" to="/login">
                {t('nav.startTrial')}
              </Link>
            </>
          )}
          <button
            type="button"
            className="icon-button pub-menu-button"
            aria-expanded={open}
            aria-label={open ? t('nav.closeMenu') : t('nav.openMenu')}
            aria-controls="site-menu"
            onClick={() => setOpen((value) => !value)}
          >
            <Icon name={open ? 'x' : 'menu'} />
          </button>
        </div>
        <span className="pub-progress" aria-hidden="true" />
      </div>
      {open && (
        <div className="pub-menu" id="site-menu">
          <nav aria-label={t('nav.menu')}>
            {PUBLIC_NAV.map((item) => (
              <NavLink key={item.key} to={item.to} onClick={close}>
                {t(`nav.${item.key}`)}
              </NavLink>
            ))}
          </nav>
          {!user && (
            <div className="pub-menu-actions">
              <Link className="button button-lg pub-ghost" to="/login" onClick={close}>
                {t('nav.signIn')}
              </Link>
              <Link className="button button-lg button-accent" to="/login" onClick={close}>
                {t('nav.startTrial')}
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  )
}
