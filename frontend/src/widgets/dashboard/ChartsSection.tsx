/**
 * "Where the money went" (spec 010, T010-05, AC-010-12): the money flow, money in and out by month
 * and the cash-flow statement for the dashboard's period. The framework switch starts at the
 * workspace's framework and never changes the workspace setting.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Framework } from '../../entities/insight'
import { SegmentedControl } from '../../shared/ui'
import { MonthBarsPanel, WaterfallPanel } from '../cash-flow'
import { MoneyFlowPanel } from '../money-flow'

export function ChartsSection({ period, range, framework }: { period: string; range: string; framework?: Framework }) {
  const { t } = useTranslation('dashboard')
  const [chosen, setChosen] = useState<Framework>()
  const shown: Framework = chosen ?? framework ?? 'IFRS'
  return (
    <section className="stack gap-4" aria-labelledby="charts-h">
      <div className="section-head charts-section-head">
        <div>
          <h2 className="type-h2" id="charts-h">
            {t('charts.title')}
          </h2>
          <p>{t('charts.subtitle', { range })}</p>
        </div>
        <span className="fw-switch">
          {t('charts.framework')}
          <SegmentedControl
            ariaLabel={t('charts.framework')}
            value={shown}
            onChange={(key) => setChosen(key as Framework)}
            options={[
              { key: 'IFRS', label: t('charts.frameworks.IFRS') },
              { key: 'US_GAAP', label: t('charts.frameworks.US_GAAP') },
            ]}
          />
        </span>
      </div>
      <div className="charts">
        <MoneyFlowPanel period={period} framework={shown} />
        <MonthBarsPanel period={period} framework={shown} />
        <WaterfallPanel period={period} framework={shown} />
      </div>
    </section>
  )
}
