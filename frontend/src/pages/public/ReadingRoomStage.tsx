import { PaperArtefact } from '../../widgets/public/PaperArtefact'

const ROWS = [0, 1, 2, 3, 4] as const

/**
 * The decorative 3D scene of the landing's reading room (spec 018, AC-018-4; docs/12 §12). Four
 * sheets, the statement's two reading layers (image and text), the beams between them, the lamp and
 * a tick per sheet; `kit.css` arranges them by the story's `data-chapter`. No words, no meaning of its
 * own: the chapters beside it carry the story.
 */
export function ReadingRoomStage() {
  return (
    <>
      <i className="rr-month" />
      <div className="rr-sheet rr-s1">
        <PaperArtefact kind="statement" />
        <div className="rr-layer is-image">
          {ROWS.map((row) => (
            <i key={row} className="rr-row" />
          ))}
        </div>
        <div className="rr-layer is-text">
          {ROWS.map((row) => (
            <i key={row} className={row === 2 ? 'rr-row is-conflict' : 'rr-row'} />
          ))}
        </div>
        <i className="rr-tick" />
      </div>
      <div className="rr-sheet rr-s2">
        <PaperArtefact kind="invoice" />
        <i className="rr-tick" />
      </div>
      <div className="rr-sheet rr-s3">
        <PaperArtefact kind="receipt" />
        <i className="rr-tick" />
      </div>
      <div className="rr-sheet rr-s4">
        <PaperArtefact kind="ledger" />
        <i className="rr-tick" />
      </div>
      <div className="rr-beams">
        <i />
        <i />
        <i />
      </div>
      <i className="rr-lamp" />
    </>
  )
}
