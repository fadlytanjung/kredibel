/**
 * A textless paper sheet built from the product's shapes (spec 018; docs/12 §12): a statement, an
 * invoice, a receipt or a ledger export. Purely decorative — hidden from assistive technology and
 * carrying no words, so it never repeats what the page says.
 */
export type ArtefactKind = 'statement' | 'invoice' | 'receipt' | 'ledger'

export interface PaperArtefactProps {
  kind: ArtefactKind
  /** A held copy carries a ring stamp; a checked sheet carries the k-tick. */
  stamp?: 'held' | 'checked'
  className?: string
}

export function PaperArtefact({ kind, stamp, className }: PaperArtefactProps) {
  return (
    <div
      className={className ? `pub-artefact ${className}` : 'pub-artefact'}
      data-kind={kind}
      data-stamp={stamp}
      aria-hidden="true"
    >
      <i className="pub-art-head" />
      <i className="pub-art-lines" />
      <i className="pub-art-total" />
    </div>
  )
}
