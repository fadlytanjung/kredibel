import { Icon } from './Icon'

/**
 * The two readings of a printed value side by side (docs/12 §6.2 readings table, spec 020): the AI
 * reader and the witness, and the result. A CRITICAL accusation is only made on values both readings
 * agree on; this table is how that is shown.
 */
export interface ReadingsPairRow {
  label: string
  aiReader: string
  witness: string
  result: string
  agreed?: boolean
}

export interface ReadingsPairProps {
  caption: string
  headers: { field: string; ai: string; witness: string; result: string }
  rows: ReadingsPairRow[]
}

export function ReadingsPair({ caption, headers, rows }: ReadingsPairProps) {
  return (
    <div className="panel panel-pad">
      <h3 className="type-h3">{caption}</h3>
      <table className="readings">
        <thead>
          <tr>
            <th scope="col">{headers.field}</th>
            <th scope="col">
              <span className="src">
                <Icon name="ai-reader" size="sm" />
                {headers.ai}
              </span>
            </th>
            <th scope="col">
              <span className="src">
                <Icon name="text-layer" size="sm" />
                {headers.witness}
              </span>
            </th>
            <th scope="col">{headers.result}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td className="amt">{row.aiReader}</td>
              <td className="amt">{row.witness}</td>
              <td>
                <span className={row.agreed ? 'status-line ok' : 'status-line wait'}>
                  <Icon name={row.agreed ? 'check' : 'circle-alert'} size="sm" />
                  {row.result}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
