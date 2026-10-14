import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { useMonths } from '../entities/month'
import { useAuth } from '../entities/session'
import { AccountClassifications, ProfitLossPanel, ProfitLossSources } from '../widgets/profit-loss'

function normalizePeriodInput(raw: string): string {
  const cleaned = raw.trim()
  if (!cleaned) return 'recent'
  if (cleaned.toLowerCase() === 'recent') return 'recent'
  if (cleaned.toLowerCase() === 'all') return 'all'
  const rangeMatch = cleaned.match(/(\d{4}-(?:0[1-9]|1[0-2]))\s*\.\.\s*(\d{4}-(?:0[1-9]|1[0-2]))/)
  if (rangeMatch) return `${rangeMatch[1]}..${rangeMatch[2]}`
  const qMatch = cleaned.match(/(\d{4})-?Q([1-4])/i)
  if (qMatch) return `${qMatch[1]}-Q${qMatch[2]}`
  const monthMatch = cleaned.match(/\b(\d{4}-(?:0[1-9]|1[0-2]))\b/)
  if (monthMatch) return monthMatch[1]
  const yearMatch = cleaned.match(/\b(20\d{2})\b/)
  if (yearMatch) return yearMatch[1]
  return cleaned
}

export function ProfitLossPage() {
  const { me } = useAuth()
  return <ProfitLossContent canEdit={me?.role === 'owner' || me?.role === 'accountant'} />
}

export function ProfitLossContent({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const [params, setParams] = useSearchParams()
  const { data: monthsData } = useMonths()
  const months = monthsData?.items?.map((m) => m.month) ?? []
  const defaultPeriod = months.length > 0 ? months[months.length - 1] : 'recent'
  const period = params.get('period') || defaultPeriod
  const [input, setInput] = useState(period)

  const handleApply = (raw: string) => {
    const resolved = normalizePeriodInput(raw)
    setInput(resolved)
    setParams({ period: resolved })
  }

  return (
    <div className="page stack gap-5">
      <div className="page-head">
        <h1 className="type-title">{t('pageTitle')}</h1>
        <p>{t('pageHelp')}</p>
      </div>
      <form
        className="row"
        onSubmit={(event) => {
          event.preventDefault()
          handleApply(input)
        }}
      >
        {months.length > 0 && (
          <label className="field">
            {t('selectMonth')}
            <select
              className="input"
              value={months.includes(period) ? period : ''}
              onChange={(event) => {
                if (event.target.value) {
                  handleApply(event.target.value)
                }
              }}
            >
              <option value="">{t('chooseMonth')}</option>
              {months.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="field">
          {t('period')}
          <input
            className="input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            aria-describedby="pnl-period-help"
          />
        </label>
        <button type="submit" className="button button-secondary">
          {t('apply')}
        </button>
      </form>
      <p id="pnl-period-help" className="muted">
        {t('periodHelp')}
      </p>
      <ProfitLossPanel period={period} detail />
      <AccountClassifications canEdit={canEdit} />
      <ProfitLossSources period={period} />
    </div>
  )
}
