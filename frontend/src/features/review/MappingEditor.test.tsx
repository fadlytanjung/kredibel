/**
 * MappingEditor (spec 005, T005-11; AC-005-11): the proposal's columns, what a choice does to the
 * sample rows, the amount layouts, and the completeness rule the API applies.
 */

import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { LedgerMapping, LedgerMappingView } from '../../entities/document'
import { isComplete } from './mapping'
import { MappingEditor } from './MappingEditor'

const HEADER = ['Tanggal', 'Uraian Transaksi', 'Kode Akun', 'Nama Akun', 'Debet', 'Kredit']
const PROPOSAL: LedgerMapping = {
  date: 'Tanggal',
  description: '',
  accountCode: 'Kode Akun',
  accountName: 'Nama Akun',
  reference: null,
  debit: 'Debet',
  credit: 'Kredit',
  amount: null,
  signConvention: null,
  dateFormat: 'DD/MM/YYYY',
  decimalSeparator: ',',
}
const VIEW: LedgerMappingView = {
  docId: 'doc_gl_new',
  layoutSignature: 'sig_q2',
  status: 'PROPOSED',
  mapping: PROPOSAL,
  header: HEADER,
  sampleRows: [
    {
      raw: ['01/04/2026', 'Penjualan kopi', '4000', 'Penjualan', '0,00', '24.480.000,00'],
      parsed: { date: '2026-04-01', accountCode: '4000', description: '', debit: { amount: '0.00', currency: '' }, credit: { amount: '24480000.00', currency: '' } },
      error: null,
    },
    { raw: ['xx/04/2026', 'Sewa gudang', '6050', 'Sewa', '15.000.000,00', '0,00'], error: "date 'xx/04/2026' is not DD/MM/YYYY" },
  ],
}

describe('MappingEditor', () => {
  it('shows the proposal, the file values beside each choice and the rows as read', () => {
    render(<MappingEditor view={VIEW} value={PROPOSAL} onChange={() => {}} />)
    expect(screen.getByLabelText('Date')).toHaveValue('Tanggal')
    expect(screen.getByLabelText('Description')).toHaveValue('')
    expect(screen.getByLabelText('Debit')).toHaveValue('Debet')
    expect(screen.getByText('1 Apr 2026 · 4000 · Credit 24,480,000')).toBeInTheDocument()
    expect(screen.getByText("Could not be read: date 'xx/04/2026' is not DD/MM/YYYY")).toBeInTheDocument()
    const [fields] = screen.getAllByRole('table') // the first table lists the fields
    expect(within(fields).getByText('Date *')).toBeInTheDocument()
  })

  it('a column choice and the amount layout go back to the panel', () => {
    const onChange = vi.fn()
    render(<MappingEditor view={VIEW} value={PROPOSAL} onChange={onChange} />)
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Uraian Transaksi' } })
    expect(onChange).toHaveBeenLastCalledWith({ ...PROPOSAL, description: 'Uraian Transaksi' })
    fireEvent.click(screen.getByLabelText('One signed amount column'))
    expect(onChange).toHaveBeenLastCalledWith({ ...PROPOSAL, debit: null, credit: null, signConvention: 'DEBIT_POSITIVE' })
    expect(screen.getByLabelText('Amount')).toBeInTheDocument()
    expect(screen.getByLabelText('Positive amounts are')).toHaveValue('DEBIT_POSITIVE')
  })

  it('is complete only with the required columns and one amount layout, like the API', () => {
    expect(isComplete(PROPOSAL)).toBe(false)
    expect(isComplete({ ...PROPOSAL, description: 'Uraian Transaksi' })).toBe(true)
    expect(isComplete({ ...PROPOSAL, description: 'Uraian Transaksi', credit: null })).toBe(false)
    expect(isComplete({ ...PROPOSAL, description: 'Uraian Transaksi', debit: null, credit: null, amount: 'Debet' })).toBe(true)
    expect(isComplete({ ...PROPOSAL, description: 'Uraian Transaksi', amount: 'Debet' })).toBe(false)
  })

  it('says how many rows the last mapping could not read when the item reopened', () => {
    render(<MappingEditor view={VIEW} value={PROPOSAL} onChange={() => {}} badRows={[3, 4, 5]} />)
    expect(screen.getByRole('status')).toHaveTextContent('3 rows could not be read with the last mapping; check the columns.')
  })
})
