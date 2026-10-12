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
import { DataTable, type DataTableColumn, type DataTableFilter } from '../../shared/ui'
import { Badge } from '../../shared/ui/Badge'
import { Field, Input } from '../../shared/ui/Field'
import { Icon } from '../../shared/ui/Icon'
import { Skeleton } from '../../shared/ui/Skeleton'

/** The actions cell of one account: edit nickname and ledger code, or remove it (state per row). */
function AccountActions({ account }: { account: BankAccount }) {
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
    <>
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
    </>
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
  const all = accounts.data ?? []
  const bySource = (source: BankAccount['source']) => (account: BankAccount) => account.source === source
  const filters: DataTableFilter<BankAccount>[] = [
    { key: 'all', label: t('bank.filterAll'), predicate: () => true, count: all.length },
    { key: 'declared', label: t('bank.declared'), predicate: bySource('DECLARED'), count: all.filter(bySource('DECLARED')).length },
    { key: 'detected', label: t('bank.detected'), predicate: bySource('DETECTED'), count: all.filter(bySource('DETECTED')).length },
  ]
  const columns: DataTableColumn<BankAccount>[] = [
    {
      key: 'account',
      header: t('bank.colAccount'),
      sortable: true,
      sortValue: (account) => (account.nickname || account.bankName).toLowerCase(),
      render: (account) => (
        <span className="doc-cell">
          <span className="thumb">
            <Icon name="bank" />
          </span>
          <span>
            <strong>{account.nickname || account.bankName}</strong>
            <span className="sub">
              {t('bank.subline', { bank: account.bankName, masked: account.accountMasked, holder: account.holderName })}
            </span>
          </span>
        </span>
      ),
    },
    {
      key: 'source',
      header: t('bank.colSource'),
      render: (account) => (
        <Badge variant={account.source === 'DETECTED' ? 'evidence' : 'default'}>
          {account.source === 'DETECTED' ? t('bank.detected') : t('bank.declared')}
        </Badge>
      ),
    },
    {
      key: 'ledger',
      header: t('bank.colLedger'),
      render: (account) => <span className="muted">{account.ledgerAccountCode || t('bank.noLedgerCode')}</span>,
    },
    {
      key: 'actions',
      header: t('bank.colActions'),
      align: 'right',
      wideOnMobile: true,
      render: (account) => <AccountActions account={account} />,
    },
  ]

  return (
    <div className="stack gap-4">
      <p className="muted">{t('bank.intro')}</p>
      {accounts.isLoading ? (
        <Skeleton className="h-24" />
      ) : accounts.data && accounts.data.length > 0 ? (
        <DataTable
          data={accounts.data}
          columns={columns}
          getRowKey={(account) => account.accountId}
          filters={filters}
          filterGroupAriaLabel={t('bank.filterLabel')}
          searchable
          searchPlaceholder={t('bank.search')}
          searchPredicate={(account, q) =>
            [account.nickname, account.bankName, account.accountMasked, account.holderName, account.ledgerAccountCode]
              .filter(Boolean)
              .some((text) => String(text).toLowerCase().includes(q))
          }
        />
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
