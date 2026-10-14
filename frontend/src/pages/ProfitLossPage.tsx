import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { AccountClassifications, ProfitLossPanel, ProfitLossSources } from '../widgets/profit-loss'

export function ProfitLossPage() {
  const { me } = useAuth()
  return <ProfitLossContent canEdit={me?.role === 'owner' || me?.role === 'accountant'} />
}

export function ProfitLossContent({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const [params, setParams] = useSearchParams()
  const period = params.get('period') || 'recent'
  const [input, setInput] = useState(period)
  return <div className="page stack gap-5">
    <div className="page-head"><h1 className="type-title">{t('pageTitle')}</h1><p>{t('pageHelp')}</p></div>
    <form className="row" onSubmit={(event) => { event.preventDefault(); setParams({ period: input }) }}>
      <label className="field">{t('period')}<input className="input" value={input} onChange={(event) => setInput(event.target.value)} aria-describedby="pnl-period-help" /></label>
      <button type="submit" className="button button-secondary">{t('apply')}</button>
    </form>
    <p id="pnl-period-help" className="muted">{t('periodHelp')}</p>
    <ProfitLossPanel period={period} detail />
    <AccountClassifications canEdit={canEdit} />
    <ProfitLossSources period={period} />
  </div>
}
