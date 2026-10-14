import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { type Accounts, useConfirmClassification, useProfitLossAccounts } from '../../entities/profit-loss'

type Account = Accounts['accounts'][number]
function AccountForm({ account, catalog, canEdit }: { account: Account; catalog: Accounts; canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const [line, setLine] = useState(account.classification?.pnlLine ?? '')
  const [subledger, setSubledger] = useState(account.classification?.subledger ?? '')
  const confirm = useConfirmClassification()
  return <form className="pnl-account" onSubmit={(event) => {
    event.preventDefault()
    confirm.mutate({ accountCode: account.accountCode, pnlLine: line, subledger })
  }}>
    <strong>{account.accountCode} {account.accountName}</strong>
    <label className="field">{t('line')}<select className="input" aria-label={t('line')} value={line} disabled={!canEdit || confirm.isPending} onChange={(event) => { setLine(event.target.value); confirm.reset() }} required>
      <option value="">{t('choose')}</option>{Object.entries(catalog.pnlLines).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </select></label>
    <label className="field">{t('subledger')}<select className="input" aria-label={t('subledger')} value={subledger} disabled={!canEdit || confirm.isPending} onChange={(event) => { setSubledger(event.target.value); confirm.reset() }} required>
      <option value="">{t('choose')}</option>{Object.entries(catalog.subledgers).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
    </select></label>
    {canEdit && <button className="button button-primary" type="submit" disabled={!line || !subledger || confirm.isPending}>{t(confirm.isPending ? 'saving' : 'confirm')}</button>}
    {confirm.isSuccess && <p role="status">{t('saved')}</p>}
    {confirm.isError && <p role="alert">{t('saveError')}</p>}
  </form>
}

export function AccountClassifications({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const query = useProfitLossAccounts()
  return <section className="panel panel-pad stack gap-4">
    <h2 className="type-h2">{t('accounts')}</h2><p>{t('accountHelp')}</p>
    {!canEdit && <p>{t('readOnly')}</p>}
    {query.isPending && <p role="status">{t('loading')}</p>}
    {query.isError && <p role="alert">{t('error')} <button className="button button-secondary" onClick={() => void query.refetch()}>{t('retry')}</button></p>}
    {query.data && (query.data.accounts.length ? query.data.accounts.map((account) => <AccountForm key={account.accountCode} account={account} catalog={query.data} canEdit={canEdit} />) : <p>{t('noAccounts')}</p>)}
  </section>
}
