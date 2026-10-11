import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../app/providers/useAuth'
import { Button } from '../shared/ui/Button'

export function OnboardingPage() {
  const { signOut, user } = useAuth()
  const navigate = useNavigate()

  const [workspaceType, setWorkspaceType] = useState<'company' | 'individual'>('company')
  const [legalName, setLegalName] = useState('Sunrise Coffee Roasters')
  const [tradingName, setTradingName] = useState('')
  const [industry, setIndustry] = useState('Food and drink, wholesale')
  const [timeZone, setTimeZone] = useState('Asia/Jakarta (UTC+7)')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Navigate to dashboard
    navigate('/')
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-canvas">
      {/* Brand Hero Column (Matching design/mocks/onboarding.html) */}
      <section className="hidden md:flex md:w-5/12 lg:w-1/2 bg-brand text-on-brand p-8 lg:p-12 flex-col justify-between">
        <div>
          <img
            src="/brand/kredibel-logo-on-dark.svg"
            alt="Kredibel"
            className="h-10 mb-8"
          />
          <div className="space-y-6">
            <p className="text-xl lg:text-2xl font-semibold tracking-tight">
              Every number has a source.
            </p>
            <ul className="space-y-4 text-sm text-on-brand/90">
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <rect x="8" y="8" width="12" height="12" rx="2" />
                  <path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8" />
                </svg>
                <span>Send the same file twice and it is never counted twice.</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
                  <circle cx="12" cy="12" r="1" />
                </svg>
                <span>Every number is read twice before it counts, and you can see where it came from.</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d="M4 7h11.5M12 3.5 15.5 7 12 10.5" />
                  <path d="M20 17H8.5M12 13.5 8.5 17l3.5 3.5" />
                </svg>
                <span>Months reconcile themselves, in any upload order. You only fix what is left.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Live Ledger preview */}
        <div className="my-8 rounded-sm bg-on-brand/10 p-4 font-mono text-xs space-y-2 border border-on-brand/15">
          <div className="flex items-center justify-between text-on-brand/90">
            <span>05 Mar</span>
            <span className="truncate mx-2">TRANSFER OUT GREEN VALLEY</span>
            <span className="font-semibold text-brand-accent">32,100,000</span>
          </div>
          <div className="flex items-center justify-between text-on-brand/90">
            <span>11 Mar</span>
            <span className="truncate mx-2">TRANSFER IN DAYBREAK CAFE</span>
            <span className="font-semibold text-brand-accent">6,420,000</span>
          </div>
          <div className="flex items-center justify-between text-on-brand/70">
            <span>12 Mar</span>
            <span className="truncate mx-2">ACB_Feb_2026 (1).pdf</span>
            <span className="text-on-brand/50">copy, not read</span>
          </div>
        </div>

        <p className="text-xs text-on-brand/60">
          Synthetic data only. Kredibel never moves money and never changes your accounting system.
        </p>
      </section>

      {/* Onboarding Form Column */}
      <main className="flex-1 flex items-center justify-center p-6 md:p-12 overflow-y-auto">
        <div className="w-full max-w-xl bg-surface p-8 rounded-md border border-line shadow-raised">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-ink">
              Whose books are these?
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              One workspace is one business or one person. You can add details later; Kredibel will suggest them from your documents.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {/* Myself vs Company Selection */}
            <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label="Workspace type">
              <button
                type="button"
                onClick={() => setWorkspaceType('individual')}
                className={`p-4 rounded-xs border text-left transition-colors cursor-pointer ${
                  workspaceType === 'individual'
                    ? 'border-brand bg-brand-soft ring-1 ring-brand'
                    : 'border-line bg-surface hover:bg-sunken'
                }`}
              >
                <div className="font-semibold text-sm text-ink mb-1">Myself</div>
                <div className="text-xs text-ink-muted leading-relaxed">
                  A freelancer or sole trader with a business account
                </div>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceType('company')}
                className={`p-4 rounded-xs border text-left transition-colors cursor-pointer ${
                  workspaceType === 'company'
                    ? 'border-brand bg-brand-soft ring-1 ring-brand'
                    : 'border-line bg-surface hover:bg-sunken'
                }`}
              >
                <div className="font-semibold text-sm text-ink mb-1">A company</div>
                <div className="text-xs text-ink-muted leading-relaxed">
                  A partnership or a limited company
                </div>
              </button>
            </div>

            {/* Form Fields */}
            <div className="space-y-4">
              <div>
                <label htmlFor="legalName" className="block text-xs font-semibold text-ink mb-1">
                  Legal name
                </label>
                <input
                  id="legalName"
                  type="text"
                  required
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
                />
              </div>

              <div>
                <label htmlFor="tradingName" className="block text-xs font-semibold text-ink mb-1">
                  Trading name <span className="text-ink-subtle font-normal">(optional)</span>
                </label>
                <input
                  id="tradingName"
                  type="text"
                  placeholder="As on your invoices"
                  value={tradingName}
                  onChange={(e) => setTradingName(e.target.value)}
                  className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="industry" className="block text-xs font-semibold text-ink mb-1">
                    Industry
                  </label>
                  <select
                    id="industry"
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
                  >
                    <option>Food and drink, wholesale</option>
                    <option>Retail & E-commerce</option>
                    <option>Professional services</option>
                    <option>Manufacturing</option>
                  </select>
                </div>

                <div>
                  <label htmlFor="timeZone" className="block text-xs font-semibold text-ink mb-1">
                    Time zone
                  </label>
                  <select
                    id="timeZone"
                    value={timeZone}
                    onChange={(e) => setTimeZone(e.target.value)}
                    className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
                  >
                    <option>Asia/Jakarta (UTC+7)</option>
                    <option>Asia/Singapore (UTC+8)</option>
                    <option>UTC (UTC+0)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Trial Note */}
            <div className="p-3 rounded-xs bg-sunken text-xs text-ink-muted flex items-start gap-2.5">
              <svg className="w-4 h-4 shrink-0 text-brand mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
              <span>
                <strong className="text-ink">30-day free trial.</strong> 150 documents and 400 pages a month. No card, no payment.
              </span>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                onClick={() => signOut()}
                className="text-xs text-ink-muted hover:text-ink cursor-pointer"
              >
                Sign out ({user?.email})
              </button>

              <Button type="submit" variant="primary" size="lg">
                Start the free trial &rarr;
              </Button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}
