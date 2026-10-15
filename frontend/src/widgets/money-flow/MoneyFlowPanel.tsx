/**
 * "Money flow" (spec 010, T010-05, AC-010-5…7, AC-010-12; mock dashboard.html): four views of
 * where the money went in a period, Flow (the Sankey), Bars, Table and By client and supplier;
 * every band, bar and row opens its bank lines.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { type FlowView, type Framework, useMoneyFlow } from '../../entities/insight'
import { SegmentedControl } from '../../shared/ui'
import { FlowLinesSheet } from './FlowLinesSheet'
import { FlowList, FlowTable, StatementBars } from './FlowViews'
import { SankeyChart } from './SankeyChart'
import { unitFor } from './units'

type Tab = 'flow' | 'bars' | 'table' | 'parties'
const TABS: Tab[] = ['flow', 'bars', 'table', 'parties']

export function MoneyFlowPanel({ period, framework }: { period: string; framework?: Framework }) {
  const { t } = useTranslation('dashboard')
  const [tab, setTab] = useState<Tab>('flow')
  const [open, setOpen] = useState<{ id: string; title: string }>()
  const view: FlowView = tab === 'parties' ? 'COUNTERPARTIES' : 'STATEMENT'
  const { data: flow, isLoading } = useMoneyFlow(period, view, framework)
  const unit = unitFor((flow?.nodes ?? []).map((n) => n.value?.amount ?? '0'))
  const columns =
    view === 'STATEMENT'
      ? [t('charts.columns.source'), t('charts.columns.account'), t('charts.columns.activity', { framework: t(`charts.frameworks.${framework ?? 'IFRS'}`) }), t('charts.columns.line')]
      : [t('charts.columns.source'), t('charts.columns.account'), t('charts.columns.use')]
  const onOpen = (id: string, title: string) => setOpen({ id, title })
  const empty = !isLoading && (flow?.links.length ?? 0) === 0

  return (
    <section className="chart-panel" aria-labelledby="money-flow-h">
      <div className="chart-head">
        <div>
          <h3 id="money-flow-h">{t('charts.flowTitle')}</h3>
          <p>{t(`charts.flowSubtitle.${tab}`)}</p>
        </div>
        <SegmentedControl
          ariaLabel={t('charts.viewLabel')}
          value={tab}
          onChange={(key) => setTab(key as Tab)}
          options={TABS.map((key) => ({ key, label: t(`charts.views.${key}`) }))}
        />
      </div>
      {isLoading && <p className="muted p-5">{t('charts.loading')}</p>}
      {empty && <p className="muted p-5">{t('charts.noFlow')}</p>}
      {flow && !empty && (
        <>
          {(tab === 'flow' || tab === 'parties') && (
            <>
              <div className="chart-compact">
                <FlowList flow={flow} unit={unit} onOpen={onOpen} />
              </div>
              <div className="chart-medium">
                <SankeyChart flow={flow} unit={unit} width={760} columns={columns} onOpen={onOpen} />
              </div>
              <div className="chart-wide">
                <SankeyChart flow={flow} unit={unit} width={1100} columns={columns} onOpen={onOpen} />
              </div>
            </>
          )}
          {tab === 'bars' && <StatementBars flow={flow} unit={unit} onOpen={onOpen} />}
          {tab === 'table' && <FlowTable flow={flow} unit={unit} onOpen={onOpen} />}
          <div className="chart-foot">
            <p className="chart-note">
              {[t(`charts.units.${unit.key}Note`), flow.note].filter(Boolean).join(' ')}
            </p>
          </div>
        </>
      )}
      {open && (
        <FlowLinesSheet
          flowId={open.id}
          title={open.title}
          period={period}
          view={view}
          framework={framework}
          onClose={() => setOpen(undefined)}
        />
      )}
    </section>
  )
}
