/** A month's open findings, most severe first, each opening its evidence (spec 007, T007-10d). */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type Finding, SeverityBadge, type SeverityLevel } from '../../entities/finding'

export function MonthFindings({ findings }: { findings: Finding[] }) {
  const { t } = useTranslation('months')
  if (findings.length === 0) return <p className="muted">{t('monthDetail.findings.none')}</p>
  return (
    <section className="panel">
      <ul className="alert-list">
        {findings.map((f) => (
          <li key={f.findingId}>
            <Link to={`/risk/${f.findingId}`}>
              <span className="sev">
                <SeverityBadge severity={f.severity as SeverityLevel} />
              </span>
              <span>
                <p className="a-t">{f.title}</p>
                {f.nextSteps?.[0] && <p className="a-s">{f.nextSteps[0]}</p>}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
