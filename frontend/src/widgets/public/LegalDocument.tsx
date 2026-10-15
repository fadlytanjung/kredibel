import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useScrollProgress } from '../../shared/lib/useScrollProgress'
import { PageHero } from './PageHero'

/**
 * A legal page as a reading layout (spec 020, AC-020-7; docs/12 §12): the ink hero, then the text with
 * a sticky contents rail that marks the section being read and a double-rule reading-progress line.
 * Copy comes from `public.json` under `privacy` or `terms` (`intro`, `<s>Title`, `<s>Body`).
 */
export interface LegalDocumentProps {
  ns: 'privacy' | 'terms'
  sections: readonly string[]
  crossLink: { to: string; label: string }
}

export function LegalDocument({ ns, sections, crossLink }: LegalDocumentProps) {
  const { t } = useTranslation('public')
  const layoutRef = useRef<HTMLDivElement>(null)
  const ids = useMemo(() => sections.map((s) => `${ns}-${s}`), [ns, sections])
  const active = useActiveSection(ids)
  useScrollProgress(layoutRef, { offset: ['start 30%', 'end end'] })

  return (
    <>
      <PageHero eyebrow={t(`${ns}.eyebrow`)} title={t(`${ns}.title`)}>
        <p className="pub-updated">{t(`${ns}.updated`)}</p>
      </PageHero>
      <section className="pub-section pub-paper is-sheet">
        <div ref={layoutRef} className="pub-inner pub-legal">
          <nav className="pub-toc" aria-label={t('legal.contents')}>
            <p className="pub-toc-title">{t('legal.contents')}</p>
            <div className="pub-toc-bar" aria-hidden="true" />
            <ol>
              {sections.map((s, i) => (
                <li key={s}>
                  <a href={`#${ids[i]}`} aria-current={active === ids[i] ? 'true' : undefined}>
                    {t(`${ns}.${s}Title`)}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
          <article className="pub-prose">
            <p>{t(`${ns}.intro`)}</p>
            {sections.map((s, i) => (
              <section key={s} id={ids[i]} aria-labelledby={`${ids[i]}-title`}>
                <h2 id={`${ids[i]}-title`}>{t(`${ns}.${s}Title`)}</h2>
                <p>{t(`${ns}.${s}Body`)}</p>
              </section>
            ))}
            <Link className="link" to={crossLink.to}>
              {crossLink.label}
            </Link>
          </article>
        </div>
      </section>
    </>
  )
}

/** The section nearest the top third of the window, for the contents rail. */
function useActiveSection(ids: readonly string[]): string | undefined {
  const [active, setActive] = useState<string | undefined>(ids[0])

  useEffect(() => {
    if (typeof window.IntersectionObserver !== 'function') return
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible[0]) setActive(visible[0].target.id)
      },
      { rootMargin: '-25% 0px -65% 0px' },
    )
    for (const id of ids) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }
    return () => observer.disconnect()
  }, [ids])

  return active
}
