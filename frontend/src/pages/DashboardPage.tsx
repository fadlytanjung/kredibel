import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge } from '../shared/ui/Badge'
import { Button } from '../shared/ui/Button'
import { Panel } from '../shared/ui/Panel'

export function DashboardPage() {
  const [framework, setFramework] = useState<'IFRS' | 'US_GAAP'>('IFRS')
  const [flowView, setFlowView] = useState<'flow' | 'bars' | 'table'>('flow')

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Status Hero Section */}
      <section
        className="bg-surface border border-line rounded-md p-6 lg:p-8 shadow-raised"
        aria-labelledby="status-h"
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
          Sunrise Coffee Roasters, January to June 2026
        </p>
        <h1 className="text-2xl lg:text-3xl font-bold tracking-tight mb-4" id="status-h">
          <span className="text-agreed">2 of 6 months are reconciled.</span>{' '}
          <span className="text-ink">9 things need you.</span>
        </h1>
        <ul className="space-y-2 mb-6 text-sm text-ink">
          <li className="flex items-center gap-2.5">
            <span className="w-5 h-5 rounded-full bg-critical-soft text-critical grid place-items-center shrink-0">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 7.5V13M12 16.5h.01" />
              </svg>
            </span>
            <span>
              <strong>March:</strong> the bank statement was edited after the bank issued it.
            </span>
          </li>
          <li className="flex items-center gap-2.5">
            <span className="w-5 h-5 rounded-full bg-high-soft text-high grid place-items-center shrink-0">
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 9.5v4M12 17h.01" />
              </svg>
            </span>
            <span>
              <strong>May:</strong> a supplier was paid to a bank account we have not seen for them before.
            </span>
          </li>
        </ul>
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/review">
            <Button variant="primary" size="lg">
              <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3.5 13.5 6 5.5A1.5 1.5 0 0 1 7.4 4.5h9.2A1.5 1.5 0 0 1 18 5.5l2.5 8" />
                <path d="M3.5 13.5V18A1.5 1.5 0 0 0 5 19.5h14a1.5 1.5 0 0 0 1.5-1.5v-4.5h-5a3.5 3.5 0 0 1-7 0z" />
              </svg>
              Open review (9)
            </Button>
          </Link>
          <Link to="/months">
            <Button variant="secondary" size="lg">
              See March
            </Button>
          </Link>
        </div>
      </section>

      {/* 2. Ledger Figures (Key Metrics) */}
      <section aria-label="Figures for January to June 2026">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <Panel className="p-4 bg-surface border border-line rounded-md">
            <span className="text-xs text-ink-muted flex items-center gap-1 font-medium">
              <svg className="w-3.5 h-3.5 text-agreed" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 7 7 17M7 9v8h8" />
              </svg>
              Money in
            </span>
            <div className="text-xl font-bold text-ink mt-2 num">
              <small className="text-xs font-normal text-ink-muted mr-1">IDR</small>
              1,355.8 M
            </div>
            <div className="text-xs text-agreed mt-1 font-medium flex items-center gap-1">
              <span>read twice</span>
            </div>
          </Panel>

          <Panel className="p-4 bg-surface border border-line rounded-md">
            <span className="text-xs text-ink-muted flex items-center gap-1 font-medium">
              <svg className="w-3.5 h-3.5 text-ink-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M7 17 17 7M9 7h8v8" />
              </svg>
              Money out
            </span>
            <div className="text-xl font-bold text-ink mt-2 num">
              <small className="text-xs font-normal text-ink-muted mr-1">IDR</small>
              1,286.8 M
            </div>
            <div className="text-xs text-agreed mt-1 font-medium flex items-center gap-1">
              <span>read twice</span>
            </div>
          </Panel>

          <Panel className="p-4 bg-surface border border-line rounded-md">
            <span className="text-xs text-ink-muted font-medium">Net</span>
            <div className="text-xl font-bold text-brand mt-2 num">
              <small className="text-xs font-normal text-ink-muted mr-1">IDR</small>
              +69.0 M
            </div>
            <div className="text-xs text-ink-muted mt-1">Kept in account</div>
          </Panel>

          <Panel className="p-4 bg-surface border border-line rounded-md">
            <span className="text-xs text-ink-muted font-medium">Matched</span>
            <div className="text-xl font-bold text-ink mt-2 num">89.6%</div>
            <div className="w-full bg-sunken rounded-full h-1.5 mt-2">
              <div className="bg-brand h-1.5 rounded-full" style={{ width: '89.6%' }} /* allow-raw-style: computed meter width */ />
            </div>
            <div className="text-xs text-ink-muted mt-1">242 of 270 lines</div>
          </Panel>

          <Panel className="p-4 bg-surface border border-line rounded-md ring-1 ring-critical/20">
            <span className="text-xs font-semibold text-critical">Needs you</span>
            <div className="text-xl font-bold text-critical mt-2 num">9</div>
            <div className="text-xs text-ink-muted mt-1">4 copies, 5 to fix</div>
          </Panel>

          <Panel className="p-4 bg-surface border border-line rounded-md">
            <span className="text-xs text-ink-muted font-medium">Documents</span>
            <div className="text-xl font-bold text-ink mt-2 num">92</div>
            <div className="text-xs text-ink-muted mt-1">1 still reading</div>
          </Panel>
        </div>
      </section>

      {/* 3. Action Lists: Needs You & Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel className="p-6 bg-surface border border-line rounded-md shadow-xs">
          <div className="flex items-center justify-between pb-4 border-b border-line mb-4">
            <h2 className="text-base font-bold text-ink">Needs you</h2>
            <Link to="/review" className="text-xs font-semibold text-brand hover:underline">
              All 9 &rarr;
            </Link>
          </div>
          <ul className="space-y-3">
            <li>
              <Link
                to="/review"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <span className="w-7 h-7 rounded-full bg-brand-soft text-brand grid place-items-center shrink-0 mt-0.5">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
                    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
                  </svg>
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    IDR 7,250,000 on 14 Mar differs from your ledger
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    Harborview Hotel Group; the March statement looks edited
                  </p>
                </div>
              </Link>
            </li>
            <li>
              <Link
                to="/review"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <span className="w-7 h-7 rounded-full bg-sunken text-ink grid place-items-center shrink-0 mt-0.5">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="8" y="8" width="12" height="12" rx="2" />
                    <path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8" />
                  </svg>
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    Possible copy of the February statement
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    ACB_Feb_2026 (re-download).pdf has the same 45 lines
                  </p>
                </div>
              </Link>
            </li>
            <li>
              <Link
                to="/review"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <span className="w-7 h-7 rounded-full bg-brand-soft text-brand grid place-items-center shrink-0 mt-0.5">
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
                    <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
                  </svg>
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    IDR 18,700,000 on 9 Feb fits two invoices
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    Daybreak Café, invoices 0003 and 0004
                  </p>
                </div>
              </Link>
            </li>
          </ul>
        </Panel>

        <Panel className="p-6 bg-surface border border-line rounded-md shadow-xs">
          <div className="flex items-center justify-between pb-4 border-b border-line mb-4">
            <h2 className="text-base font-bold text-ink">Risk</h2>
            <Link to="/risk" className="text-xs font-semibold text-brand hover:underline">
              All findings &rarr;
            </Link>
          </div>
          <ul className="space-y-3">
            <li>
              <Link
                to="/risk"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <Badge variant="critical">Critical</Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    March statement edited after the bank issued it
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    Balance breaks on 14 Mar; later revision in a PDF editor
                  </p>
                </div>
              </Link>
            </li>
            <li>
              <Link
                to="/risk"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <Badge variant="high">High</Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    Roastline Equipment Service paid to new account
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    6 May, IDR 24,500,000 to Meridian Savings ••7720
                  </p>
                </div>
              </Link>
            </li>
            <li>
              <Link
                to="/risk"
                className="flex items-start gap-3 p-2.5 rounded-xs hover:bg-sunken transition-colors"
              >
                <Badge variant="medium">Medium</Badge>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-ink leading-tight">
                    Invoices from an unknown supplier
                  </p>
                  <p className="text-xs text-ink-muted mt-0.5 truncate">
                    Bluewater Trading Co., 2 invoices, never paid
                  </p>
                </div>
              </Link>
            </li>
          </ul>
        </Panel>
      </div>

      {/* 4. "Where the Money Went" Charts Section */}
      <section className="bg-surface border border-line rounded-md p-6 lg:p-8 shadow-raised">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-line mb-6">
          <div>
            <h2 className="text-xl font-bold text-ink">Where the money went</h2>
            <p className="text-xs text-ink-muted mt-1">
              January to June 2026, IDR millions, grouped by your accounting framework.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-ink-muted">Framework</span>
            <div className="inline-flex rounded-xs border border-line p-0.5 bg-sunken">
              <button
                type="button"
                onClick={() => setFramework('IFRS')}
                className={`px-3 py-1 rounded-xs text-xs font-semibold transition-colors cursor-pointer ${
                  framework === 'IFRS' ? 'bg-surface text-ink shadow-xs' : 'text-ink-muted hover:text-ink'
                }`}
              >
                IFRS
              </button>
              <button
                type="button"
                onClick={() => setFramework('US_GAAP')}
                className={`px-3 py-1 rounded-xs text-xs font-semibold transition-colors cursor-pointer ${
                  framework === 'US_GAAP' ? 'bg-surface text-ink shadow-xs' : 'text-ink-muted hover:text-ink'
                }`}
              >
                US GAAP
              </button>
            </div>
          </div>
        </div>

        {/* Chart View Selector */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-ink">Money flow (Sankey)</h3>
            <p className="text-xs text-ink-muted">From clients through ACB ••4821 to statement lines.</p>
          </div>
          <div className="inline-flex rounded-xs border border-line p-0.5 bg-sunken">
            <button
              type="button"
              onClick={() => setFlowView('flow')}
              className={`px-2.5 py-1 text-xs font-medium rounded-xs cursor-pointer ${
                flowView === 'flow' ? 'bg-surface text-ink shadow-xs font-semibold' : 'text-ink-muted'
              }`}
            >
              Flow
            </button>
            <button
              type="button"
              onClick={() => setFlowView('bars')}
              className={`px-2.5 py-1 text-xs font-medium rounded-xs cursor-pointer ${
                flowView === 'bars' ? 'bg-surface text-ink shadow-xs font-semibold' : 'text-ink-muted'
              }`}
            >
              Bars
            </button>
          </div>
        </div>

        {/* Interactive Sankey Diagram Render */}
        <div className="overflow-x-auto bg-canvas/40 p-4 rounded-md border border-line">
          <svg
            className="w-full max-w-5xl mx-auto block"
            viewBox="0 0 1200 480"
            role="img"
            aria-label="Where the money went, January to June 2026"
          >
            {/* Headers */}
            <text x="250" y="24" textAnchor="end" className="text-xs fill-ink-muted font-semibold">
              Revenue, by client
            </text>
            <text x="480" y="24" textAnchor="middle" className="text-xs fill-ink font-semibold">
              Bank Account (ACB ••4821)
            </text>
            <text x="718" y="24" textAnchor="middle" className="text-xs fill-ink font-semibold">
              Activity ({framework})
            </text>
            <text x="950" y="24" textAnchor="start" className="text-xs fill-ink-muted font-semibold">
              Statement line
            </text>

            {/* Flows to Account */}
            <path d="M250,50 C361,50 361,80 472,80 L472,190 C361,190 361,160 250,160 Z" className="fill-brand-line opacity-40" />
            <path d="M250,170 C361,170 361,190 472,190 L472,275 C361,275 361,255 250,255 Z" className="fill-brand-line opacity-35" />
            <path d="M250,265 C361,265 361,275 472,275 L472,330 C361,330 361,320 250,320 Z" className="fill-brand-line opacity-30" />
            <path d="M250,335 C361,335 361,335 472,335 L472,380 C361,380 361,380 250,380 Z" className="fill-brand-line opacity-25" />

            {/* Flows to Activities */}
            <path d="M488,80 C600,80 600,68 712,68 L712,380 C600,380 600,392 488,392 Z" className="fill-chart-operating opacity-25" />
            <path d="M488,392 C600,392 600,410 712,410 L712,450 C600,450 600,432 488,432 Z" className="fill-chart-financing opacity-30" />
            <path d="M488,432 C600,432 600,460 712,460 L712,475 C600,475 600,447 488,447 Z" className="fill-brand-accent opacity-50" />

            {/* Node Rectangles */}
            <rect x="240" y="50" width="10" height="110" rx="2" className="fill-brand-line" />
            <rect x="240" y="170" width="10" height="85" rx="2" className="fill-brand-line" />
            <rect x="240" y="265" width="10" height="55" rx="2" className="fill-brand-line" />
            <rect x="240" y="335" width="10" height="45" rx="2" className="fill-brand-line" />

            {/* Account Node */}
            <rect x="472" y="80" width="16" height="367" rx="3" className="fill-brand" />

            {/* Activity Nodes */}
            <rect x="712" y="68" width="12" height="312" rx="2" className="fill-chart-operating" />
            <rect x="712" y="410" width="12" height="40" rx="2" className="fill-chart-financing" />
            <rect x="712" y="460" width="12" height="15" rx="2" className="fill-brand-accent" />

            {/* Labels */}
            <text x="230" y="105" textAnchor="end" className="text-xs fill-ink font-medium">Harborview Hotel (412.5 M)</text>
            <text x="230" y="215" textAnchor="end" className="text-xs fill-ink font-medium">Highland Resort (318.0 M)</text>
            <text x="230" y="295" textAnchor="end" className="text-xs fill-ink font-medium">Daybreak Café (196.4 M)</text>
            <text x="230" y="360" textAnchor="end" className="text-xs fill-ink font-medium">Spice Route (154.8 M)</text>

            <text x="735" y="225" className="text-xs fill-ink font-semibold">Operating (1,154.8 M)</text>
            <text x="735" y="432" className="text-xs fill-ink font-semibold">Financing (132.0 M)</text>
            <text x="735" y="472" className="text-xs fill-ink font-semibold">Kept (+69.0 M)</text>
          </svg>
        </div>
      </section>

      {/* 5. Month Reconciliation Strip */}
      <section aria-labelledby="months-h">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-ink" id="months-h">Months</h2>
          <Link to="/months" className="text-xs font-semibold text-brand hover:underline">
            All months &rarr;
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {[
            { name: 'Jan', status: 'Reconciled', match: '94%', count: '42/45', badge: 'low', badgeText: 'Low' },
            { name: 'Feb', status: '2 need you', match: '89%', count: '40/45', badge: 'medium', badgeText: 'Medium' },
            { name: 'Mar', status: '2 need you', match: '86%', count: '39/45', badge: 'critical', badgeText: 'Critical' },
            { name: 'Apr', status: 'Reconciled', match: '93%', count: '42/45', badge: 'low', badgeText: 'Low' },
            { name: 'May', status: '3 need you', match: '88%', count: '40/45', badge: 'high', badgeText: 'High' },
            { name: 'Jun', status: '2 need you', match: '87%', count: '39/45', badge: 'medium', badgeText: 'Medium' },
          ].map((m) => (
            <Link
              key={m.name}
              to="/months"
              className="p-3.5 bg-surface border border-line rounded-md hover:border-brand transition-colors block"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm text-ink">{m.name}</span>
                <span className="text-xs text-ink-muted">2026</span>
              </div>
              <div className={`text-xs font-medium mb-2 ${m.status === 'Reconciled' ? 'text-agreed' : 'text-critical'}`}>
                {m.status}
              </div>
              <div className="w-full bg-sunken rounded-full h-1 mb-1">
                <div className="bg-brand h-1 rounded-full" style={{ width: m.match }} /* allow-raw-style: computed meter width */ />
              </div>
              <div className="flex items-center justify-between text-xs text-ink-muted">
                <span>{m.match}</span>
                <Badge variant={m.badge as 'low' | 'medium' | 'high' | 'critical'}>{m.badgeText}</Badge>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 6. Profile Suggestions Alert */}
      <section className="bg-brand-soft border border-brand-line/30 rounded-md p-4 flex items-start gap-3">
        <svg className="w-5 h-5 text-brand shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 3.5 13.7 8.3 18.5 10l-4.8 1.7L12 16.5l-1.7-4.8L5.5 10l4.8-1.7z" />
        </svg>
        <div className="flex-1 text-xs text-ink">
          <strong>Kredibel found 2 details for your profile:</strong> your tax ID and your address, both printed on your sales invoices. Nothing changes until you accept.
        </div>
        <Link to="/settings">
          <Button variant="secondary" size="sm">Review details</Button>
        </Link>
      </section>
    </div>
  )
}
