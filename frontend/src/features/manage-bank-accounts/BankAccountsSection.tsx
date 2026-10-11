/**
 * Settings → Bank accounts (docs/11 §6.9, AC-013-14): masked accounts, declared or detected,
 * nickname and ledger account code; add one; remove one. Full numbers are sent once and never shown.
 */

import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import {
  useAddBankAccount,
  useBankAccounts,
  useDeleteBankAccount,
  useUpdateBankAccount,
  type BankAccount,
} from '../../entities/bank-account'
import { ProblemError } from '../../shared/api/client'
import { Badge } from '../../shared/ui/Badge'
import { Field, Input } from '../../shared/ui/Field'
import { Icon } from '../../shared/ui/Icon'
import { Skeleton } from '../../shared/ui/Skeleton'

function AccountRow({ account }: { account: BankAccount }) {
  const { t } = useTranslation('settings')
  const update = useUpdateBankAccount()
  const remove = useDeleteBankAccount()
  const [editing, setEditing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [nickname, setNickname] = useState(account.nickname ?? '')
  const [ledgerCode, setLedgerCode] = useState(account.ledgerAccountCode ?? '')

  const save = async (event: FormEvent) => {
    event.preventDefault()
    await update.mutateAsync({
      accountId: account.accountId,
      patch: { nickname: nickname.trim() || undefined, ledgerAccountCode: ledgerCode.trim() || null },
    })
    setEditing(false)
  }

  return (
    <tr>
      <td>
        <span className="doc-cell">
          <span className="thumb">
            <Icon name="bank" />
          </span>
          <span>
            <strong>{account.nickname || account.bankName}</strong>
            <span className="sub">
              {t('bank.subline', {
                bank: account.bankName,
                masked: account.accountMasked,
                holder: account.holderName,
              })}
            </span>
          </span>
        </span>
      </td>
      <td>
        <Badge variant={account.source === 'DETECTED' ? 'evidence' : 'default'}>
          {account.source === 'DETECTED' ? t('bank.detected') : t('bank.declared')}
        </Badge>
      </td>
      <td className="muted">{account.ledgerAccountCode || t('bank.noLedgerCode')}</td>
      <td className="r" data-cell="wide">
        {editing ? (
          <form className="row justify-end" onSubmit={save}>
            <Input
              aria-label={t('bank.nickname')}
              placeholder={t('bank.nickname')}
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              className="w-40"
            />
            <Input
              aria-label={t('bank.ledgerCode')}
              placeholder={t('bank.ledgerCode')}
              value={ledgerCode}
              onChange={(e) => setLedgerCode(e.target.value)}
              className="w-32"
            />
            <button type="submit" className="button button-primary button-sm" disabled={update.isPending}>
              {t('bank.save')}
            </button>
            <button type="button" className="button button-ghost button-sm" onClick={() => setEditing(false)}>
              {t('bank.cancel')}
            </button>
          </form>
        ) : confirming ? (
          <span className="row justify-end">
            <span className="small">{t('bank.confirmRemove', { masked: account.accountMasked })}</span>
            <button
              type="button"
              className="button button-secondary button-sm text-critical"
              disabled={remove.isPending}
              onClick={() => void remove.mutateAsync(account.accountId)}
            >
              {t('bank.remove')}
            </button>
            <button type="button" className="button button-ghost button-sm" onClick={() => setConfirming(false)}>
              {t('bank.cancel')}
            </button>
          </span>
        ) : (
          <span className="row justify-end">
            <button type="button" className="button button-ghost button-sm" onClick={() => setEditing(true)}>
              {t('bank.edit')}
            </button>
            <button type="button" className="button button-ghost button-sm" onClick={() => setConfirming(true)}>
              {t('bank.remove')}
            </button>
          </span>
        )}
      </td>
    </tr>
  )
}

function AddAccountForm({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation('settings')
  const { t: tOnboarding } = useTranslation('onboarding')
  const add = useAddBankAccount()
  const [bankName, setBankName] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [holderName, setHolderName] = useState('')
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (!/^[0-9 -]{6,30}$/.test(accountNumber)) {
      setError(tOnboarding('validation.accountNumber'))
      return
    }
    try {
      await add.mutateAsync({ bankName: bankName.trim(), accountNumber, holderName: holderName.trim() })
      onDone()
    } catch (problem) {
      setError(
        problem instanceof ProblemError && problem.code === 'BANK_ACCOUNT_EXISTS'
          ? t('bank.exists')
          : problem instanceof Error
            ? problem.message
            : t('bank.exists'),
      )
    }
  }

  return (
    <form className="panel panel-pad stack gap-4" onSubmit={submit}>
      <h3 className="type-h3">{t('bank.addTitle')}</h3>
      <div className="form-wrap">
        <div className="form-grid">
          <Field id="new-bank" label={t('bank.bankName')}>
            <Input id="new-bank" required value={bankName} onChange={(e) => setBankName(e.target.value)} />
          </Field>
          <Field id="new-holder" label={t('bank.holderName')}>
            <Input id="new-holder" required value={holderName} onChange={(e) => setHolderName(e.target.value)} />
          </Field>
          <Field
            id="new-number"
            className="span-2"
            label={t('bank.accountNumber')}
            hint={tOnboarding('accountNumberHint')}
            error={error ?? undefined}
          >
            <Input
              id="new-number"
              required
              inputMode="numeric"
              autoComplete="off"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
            />
          </Field>
        </div>
      </div>
      <div className="row">
        <button type="submit" className="button button-primary" disabled={add.isPending}>
          {add.isPending ? t('bank.adding') : t('bank.add')}
        </button>
        <button type="button" className="button button-ghost" onClick={onDone}>
          {t('bank.cancel')}
        </button>
      </div>
    </form>
  )
}

export function BankAccountsSection() {
  const { t } = useTranslation('settings')
  const accounts = useBankAccounts()
  const [adding, setAdding] = useState(false)

  return (
    <div className="stack gap-4">
      <p className="muted">{t('bank.intro')}</p>
      {accounts.isLoading ? (
        <Skeleton className="h-24" />
      ) : accounts.data && accounts.data.length > 0 ? (
        <div className="table-panel rt-wrap">
          <table className="data-table rt">
            <tbody>
              {accounts.data.map((account) => (
                <AccountRow key={account.accountId} account={account} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="panel panel-pad muted">{t('bank.empty')}</p>
      )}
      {adding ? (
        <AddAccountForm onDone={() => setAdding(false)} />
      ) : (
        <div>
          <button type="button" className="button button-secondary" onClick={() => setAdding(true)}>
            <Icon name="plus" size="sm" />
            {t('bank.add')}
          </button>
        </div>
      )}
    </div>
  )
}
