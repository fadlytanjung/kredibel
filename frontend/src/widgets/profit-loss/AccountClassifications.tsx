import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { type Accounts, useConfirmClassification, useProfitLossAccounts } from '../../entities/profit-loss'
import { OptionSelect } from '../../shared/ui'

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
          <OptionSelect
            ariaLabel={t('line')}
            value={line}
            disabled={!canEdit || confirm.isPending}
            placeholder={t('choose')}
            options={pnlOptions}
            required
            onChange={(val) => {
              setLine(val)
              confirm.reset()
            }}
          />
        </label>
      </td>
      <td>
        <label className="field m-0">
          <span className="sr-only">{t('subledger')}</span>
          <OptionSelect
            ariaLabel={t('subledger')}
            value={subledger}
            disabled={!canEdit || confirm.isPending}
            placeholder={t('choose')}
            options={subledgerOptions}
            required
            onChange={(val) => {
              setSubledger(val)
              confirm.reset()
            }}
          />
        </label>
      </td>
      {canEdit && (
        <td className="r">
          <div className="row items-center justify-end gap-2">
            <button
              className="button button-primary button-sm"
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

  return (
    <section className="panel panel-pad stack gap-4">
      <div className="spread items-center">
        <div>
          <h2 className="type-h2">{t('accounts')}</h2>
          <p className="muted small mt-1">{t('accountHelp')}</p>
        </div>
        {!canEdit && <span className="badge badge-quiet">{t('readOnly')}</span>}
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
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '30%' }} /* allow-raw-style: account column width */>{t('colAccount', { defaultValue: 'Account' })}</th>
                  <th style={{ width: '32%' }} /* allow-raw-style: line column width */>{t('line')}</th>
                  <th style={{ width: '25%' }} /* allow-raw-style: subledger column width */>{t('subledger')}</th>
                  {canEdit && (
                    <th className="r" style={{ width: '13%' }} /* allow-raw-style: action column width */>
                      {t('action', { defaultValue: 'Action' })}
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {query.data.accounts.map((account) => (
                  <AccountRow
                    key={account.accountCode}
                    account={account}
                    catalog={query.data!}
                    canEdit={canEdit}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">{t('noAccounts')}</p>
        ))}
    </section>
  )
}
