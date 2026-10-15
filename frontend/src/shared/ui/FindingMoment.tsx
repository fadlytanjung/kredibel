import type { ReactNode } from 'react'
import { Icon } from './Icon'

/**
 * A finding as the product shows it (docs/12 §6.7, spec 020): severity, the code beside the human
 * title, the consequence, a calculation of how the balance should add up, and what to do next.
 * Numbers come from code, never from a model (constitution P2).
 */
export interface FindingMomentProps {
  severityLabel: string
  code: string
  title: string
  /** The consequence, first. May contain the lamp over the printed value. */
  consequence: ReactNode
  calc: {
    prevLabel: string
    prev: string
    amountLabel: string
    amount: string
    expectedLabel: string
    expected: string
    shownLabel: string
    shown: string
    /** Column headers, read by assistive technology only: every amount has a header. */
    headers?: { op: string; line: string; amount: string }
  }
  nextLabel: string
  nextStep: string
}

export function FindingMoment({
  severityLabel,
  code,
  title,
  consequence,
  calc,
  nextLabel,
  nextStep,
}: FindingMomentProps) {
  return (
    <div className="explain">
      <div className="explain-head">
        <Icon name="octagon-alert" size="sm" />
        {severityLabel}
      </div>
      <div className="explain-body">
        <h3 className="type-h1">
          <span className="code-tag">{code}</span> {title}
        </h3>
        <p className="lead">{consequence}</p>
        <div className="calc">
          <table>
            {calc.headers && (
              <thead className="sr-only">
                <tr>
                  <th scope="col">{calc.headers.op}</th>
                  <th scope="col">{calc.headers.line}</th>
                  <th scope="col">{calc.headers.amount}</th>
                </tr>
              </thead>
            )}
            <tbody>
              <tr>
                <td className="op" />
                <th scope="row">{calc.prevLabel}</th>
                <td className="amt">{calc.prev}</td>
              </tr>
              <tr>
                <td className="op">+</td>
                <th scope="row">{calc.amountLabel}</th>
                <td className="amt">{calc.amount}</td>
              </tr>
              <tr className="total">
                <td className="op" />
                <th scope="row">{calc.expectedLabel}</th>
                <td className="amt">{calc.expected}</td>
              </tr>
              <tr className="diff">
                <td className="op" />
                <th scope="row">{calc.shownLabel}</th>
                <td className="amt">{calc.shown}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <h4 className="type-h3">{nextLabel}</h4>
          <ol className="steps">
            <li>{nextStep}</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
