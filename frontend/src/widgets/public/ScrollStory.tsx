import { useId, useRef, type ReactNode } from 'react'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { usePointerTilt } from '../../shared/lib/usePointerTilt'
import { useScrollProgress } from '../../shared/lib/useScrollProgress'

export interface StoryChapter {
  key: string
  title: string
  body: string
  /** Real content shown with the chapter (a reading table, a finding), never inside the stage. */
  extra?: ReactNode
}

export interface ScrollStoryProps {
  eyebrow: string
  title: string
  lead: string
  chapters: readonly StoryChapter[]
  /** The decorative 3D scene; it reads `data-chapter` and `--p` from the story. */
  stage: ReactNode
}

/**
 * A scroll story with a sticky 3D stage (spec 018, AC-018-4, AC-018-12; docs/12 §12). One DOM: the
 * chapters are real headings in reading order and scroll natively; beside them on wide, tall screens
 * the stage sticks and changes with the chapter in view (`data-chapter`) and the scroll (`--p`).
 * Elsewhere, and under reduced motion, the chapters simply stack and nothing pins.
 */
export function ScrollStory({ eyebrow, title, lead, chapters, stage }: ScrollStoryProps) {
  const sectionRef = useRef<HTMLElement>(null)
  const headRef = useRef<HTMLDivElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  usePointerTilt(sectionRef)
  const headView = useInViewAttr(headRef)
  const chapter = useScrollProgress(bodyRef, {
    offset: ['start center', 'end center'],
    chapters: chapters.length,
  })

  return (
    <section
      ref={sectionRef}
      className="pub-ink pub-section pub-story"
      data-chapter={chapter}
      aria-labelledby={titleId}
    >
      <div className="pub-inner">
        <div ref={headRef} className="pub-head pub-reveal" {...headView}>
          <p className="pub-eyebrow">{eyebrow}</p>
          <h2 id={titleId} className="pub-h2">
            {title}
          </h2>
          <p className="pub-lead">{lead}</p>
        </div>
        <div ref={bodyRef} className="pub-story-body">
          <div className="pub-story-aside" aria-hidden="true">
            <div className="pub-story-sticky">
              <div className="pub-story-stage">
                <div className="pub-story-cam">{stage}</div>
              </div>
              <ol className="pub-story-rail">
                {chapters.map((c) => (
                  <li key={c.key} />
                ))}
              </ol>
            </div>
          </div>
          <ol className="pub-story-chapters">
            {chapters.map((c, i) => (
              <li key={c.key} className="pub-chapter" data-active={i === chapter}>
                <span className="pub-chapter-num" aria-hidden="true">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3>{c.title}</h3>
                <p>{c.body}</p>
                {c.extra && <div className="pub-chapter-extra">{c.extra}</div>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}
