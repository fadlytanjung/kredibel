import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { type Accounts, useConfirmClassification, useProfitLossAccounts } from '../../entities/profit-loss'

type Account = Accounts['accounts'][number]

function AccountRow({ account, catalog, canEdit }: { account: Account; catalog: Accounts; canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const [line, setLine] = useState(account.classification?.pnlLine ?? '')
  const [subledger, setSubledger] = useState(account.classification?.subledger ?? '')
  const confirm = useConfirmClassification()

  const pnlOptions = Object.entries(catalog.pnlLines).map(([key, label]) => ({ value: key, label }))
  const subledgerOptions = Object.entries(catalog.subledgers).map(([key, label]) => ({ value: key, label }))

  const handleConfirm = () => {
    confirm.mutate({ accountCode: account.accountCode, pnlLine: line, subledger })
  }

  return (
    <tr key={account.accountCode}>
      <td>
        <div className="doc-cell">
          <div>
            <strong>{account.accountCode}</strong>
            <span className="sub">{account.accountName}</span>
          </div>
        </div>
      </td>
      <td>
        <label className="field m-0">
          <span className="sr-only">{t('line')}</span>
          <select className="input" aria-label={t('line')} value={line} disabled={!canEdit || confirm.isPending} required onChange={(event) => { setLine(event.target.value); confirm.reset() }}>
            <option value="">{t('choose')}</option>
            {pnlOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </td>
      <td>
        <label className="field m-0">
          <span className="sr-only">{t('subledger')}</span>
          <select className="input" aria-label={t('subledger')} value={subledger} disabled={!canEdit || confirm.isPending} required onChange={(event) => { setSubledger(event.target.value); confirm.reset() }}>
            <option value="">{t('choose')}</option>
            {subledgerOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </td>
      {canEdit && (
        <td className="r">
          <div className="row items-center justify-end gap-2">
            <button
              className="button button-primary"
              type="button"
              disabled={!line || !subledger || confirm.isPending}
              onClick={handleConfirm}
            >
              {t(confirm.isPending ? 'saving' : 'confirm')}
            </button>
            {confirm.isSuccess && (
              <span className="status-line ok small" role="status">
                {t('saved')}
              </span>
            )}
            {confirm.isError && (
              <span className="status-line bad small" role="alert">
                {t('saveError')}
              </span>
            )}
          </div>
        </td>
      )}
    </tr>
  )
}

export function AccountClassifications({ canEdit }: { canEdit: boolean }) {
  const { t } = useTranslation('profitLoss')
  const query = useProfitLossAccounts()
  // No ledger export yet: the rows are the bank-line categories with the policy's labels (cash basis).
  const cash = query.data?.basis === 'CASH'
  const editable = canEdit && !cash

  return (
    <section className="panel panel-pad stack gap-4">
      <div className="spread items-center">
        <div>
          <h2 className="type-h2">{t(cash ? 'accountsCash' : 'accounts')}</h2>
          <p className="muted small mt-1">{t(cash ? 'accountHelpCash' : 'accountHelp')}</p>
        </div>
        {cash ? <span className="badge badge-quiet">{t('fromPolicy')}</span> : !canEdit && <span className="badge badge-quiet">{t('readOnly')}</span>}
      </div>

      {query.isPending && <p role="status">{t('loading')}</p>}
      {query.isError && (
        <p role="alert">
          {t('error')}{' '}
          <button className="button button-secondary button-sm" onClick={() => void query.refetch()}>
            {t('retry')}
          </button>
        </p>
      )}

      {query.data &&
        (query.data.accounts.length ? (
          <div className="table-panel">
            <table className="data-table pnl-accounts">
              <thead>
                <tr>
                  <th>{t('colAccount', { defaultValue: 'Account' })}</th>
                  <th>{t('line')}</th>
                  <th>{t('subledger')}</th>
                  {editable && (
                    <th className="r">
                      {t('action', { defaultValue: 'Action' })}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {query.data.accounts.map((account) =>
                  cash ? (
                    <tr key={account.accountCode}>
                      <td>
                        <div className="doc-cell">
                          <div>
                            <strong>{account.accountName}</strong>
                            <span className="sub">{account.accountCode}</span>
                          </div>
                        </div>
                      </td>
                      <td>{account.classification ? query.data!.pnlLines[account.classification.pnlLine] : t('choose')}</td>
                      <td>{account.classification ? query.data!.subledgers[account.classification.subledger] : t('choose')}</td>
                    </tr>
                  ) : (
                    <AccountRow
                      key={account.accountCode}
                      account={account}
                      catalog={query.data!}
                      canEdit={canEdit}
                    />
                  ),
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">{t('noAccounts')}</p>
        ))}
    </section>
  )
}
