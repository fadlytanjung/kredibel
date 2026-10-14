import type { ReactNode } from 'react'
import { PaperArtefact, type ArtefactKind } from './PaperArtefact'

/**
 * A CSS 3D stage (spec 018, AC-018-2, AC-018-12; docs/12 §12): perspective → an entrance → a group
 * that tilts with the pointer (it reads `--rx`/`--ry` from the surrounding `Lamp`) → the leaves. The
 * `deck` is a pile of textless paper artefacts floating behind the front piece at other depths.
 */
export interface DepthStageProps {
  deck?: readonly ArtefactKind[]
  children?: ReactNode
  className?: string
}

export function DepthStage({ deck = [], children, className }: DepthStageProps) {
  return (
    <div className={className ? `pub-stage ${className}` : 'pub-stage'}>
      <div className="pub-stage-enter">
        <div className="pub-stage-tilt">
          {deck.length > 0 && (
            <div className="pub-deck" aria-hidden="true">
              {deck.map((kind, i) => (
                <PaperArtefact key={`${kind}-${i}`} kind={kind} />
              ))}
            </div>
          )}
          {children}
        </div>
      </div>
    </div>
  )
}
