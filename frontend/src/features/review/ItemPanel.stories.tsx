import type { Meta, StoryObj } from '@storybook/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReviewItem } from '../../entities/review'
import { ItemPanel } from './ItemPanel'

// Synthetic workspace (docs/18): the month's records the panel looks its subjects up in.
const idr = (amount: string) => ({ amount, currency: 'IDR' })
const MONTH = '2026-02'

function seeded() {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } })
  client.setQueryData(['bank-lines', { month: MONTH }], {
    items: [
      { txId: 'tx_9feb', docId: 'doc_feb', date: '2026-02-09', month: MONTH, description: 'TRANSFER IN HIGHLAND CAFE', amount: idr('19205109.00'), support: 'PROPOSED', match: { state: 'PROPOSED' } },
      { txId: 'tx_21feb', docId: 'doc_feb', date: '2026-02-21', month: MONTH, description: 'TRANSFER TO BLUEWATER TRADING', amount: idr('-990000.00'), support: 'NO_SUPPORT', match: { state: 'UNMATCHED' } },
      { txId: 'tx_14feb', docId: 'doc_feb', date: '2026-02-14', month: MONTH, description: 'CASH DEPOSIT', amount: idr('2150000.00'), support: 'NO_SUPPORT', match: { state: 'UNMATCHED' } },
    ],
  })
  client.setQueryData(['invoices', { month: MONTH }], {
    items: [
      { invoiceId: 'inv_0010', docId: 'doc_0010', kind: 'SALES', number: 'INV/SCR/2026/02/0010', buyerName: 'Highland Café', issueDate: '2026-02-02', month: MONTH, total: idr('19597050.00') },
      { invoiceId: 'inv_bw42', docId: 'doc_bw42', kind: 'PURCHASE', number: 'BW-0042', issuerName: 'Bluewater Trading Co.', issueDate: '2026-02-03', month: MONTH, total: idr('990000.00') },
    ],
  })
  client.setQueryData(['receipts', { month: MONTH }], {
    items: [{ receiptId: 'rcp_17feb', docId: 'doc_rcp', merchantName: 'Cendana Fuel Station', date: '2026-02-17', month: MONTH, total: idr('467976.00') }],
  })
  client.setQueryData(['document', 'doc_copy'], { docId: 'doc_copy', fileName: 'statement-2026-02 (1).pdf' })
  client.setQueryData(['document', 'doc_feb'], { docId: 'doc_feb', fileName: 'statement-2026-02.pdf' })
  // A ledger export with a new layout (spec 005, T005-11): the proposal misses the description.
  client.setQueryData(['document', 'doc_gl_new'], { docId: 'doc_gl_new', fileName: 'GL_2026_Q2.csv' })
  client.setQueryData(['ledger-mapping', 'doc_gl_new'], {
    docId: 'doc_gl_new',
    layoutSignature: 'sig_q2',
    status: 'PROPOSED',
    mapping: { date: 'Tanggal', description: null, accountCode: 'Kode Akun', accountName: 'Nama Akun', reference: null, debit: 'Debet', credit: 'Kredit', amount: null, signConvention: null, dateFormat: 'DD/MM/YYYY', decimalSeparator: ',' },
    header: ['Tanggal', 'Uraian Transaksi', 'Kode Akun', 'Nama Akun', 'Debet', 'Kredit'],
    sampleRows: [
      { raw: ['01/04/2026', 'Penjualan kopi', '4000', 'Penjualan', '0,00', '24.480.000,00'], parsed: { date: '2026-04-01', accountCode: '4000', description: '', debit: { amount: '0.00', currency: '' }, credit: { amount: '24480000.00', currency: '' } }, error: null },
      { raw: ['01/04/2026', 'Penjualan kopi', '1110', 'Bank', '24.480.000,00', '0,00'], parsed: { date: '2026-04-01', accountCode: '1110', description: '', debit: { amount: '24480000.00', currency: '' }, credit: { amount: '0.00', currency: '' } }, error: null },
    ],
    bankAccountCodes: {},
  })
  return client
}

const base = { month: MONTH, status: 'OPEN', suggestion: {} } as const

const meta: Meta<typeof ItemPanel> = {
  title: 'Features/Review/ItemPanel',
  component: ItemPanel,
  args: { position: { index: 1, total: 9 }, onResolved: () => {}, onSkip: () => {}, onClose: () => {} },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <QueryClientProvider client={seeded()}>
          <div className="review max-w-3xl p-6">
            <Story />
          </div>
        </QueryClientProvider>
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj<typeof ItemPanel>

const item = (fields: Partial<ReviewItem> & Pick<ReviewItem, 'itemId' | 'kind' | 'title' | 'subject' | 'allowedActions'>) =>
  ({ ...base, priority: 50, ...fields }) as ReviewItem

export const ProposedMatch: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000001',
      kind: 'PROPOSED_MATCH',
      title: 'Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026',
      subject: { bankLineIds: ['tx_9feb'], invoiceIds: ['inv_0010'], matchId: 'mat_feb' },
      suggestion: { candidates: [{ matchId: 'mat_feb', invoiceIds: ['inv_0010'], score: '0.82', reasons: ['NET_OF_TAX', 'PARTY_MATCH', 'DATE_NEAR'] }] },
      allowedActions: ['CONFIRM_MATCH', 'MATCH', 'REJECT_MATCH'],
    }),
  },
}

export const UnpaidDocument: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000002',
      kind: 'UNMATCHED_DOCUMENT',
      title: 'Invoice BW-0042 of IDR 990,000.00 is unpaid after its due date',
      subject: { invoiceIds: ['inv_bw42'], docIds: ['doc_bw42'] },
      allowedActions: ['MATCH', 'NOT_YET_PAID', 'IGNORE'],
    }),
  },
}

export const PossibleCopy: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000003',
      kind: 'POSSIBLE_DUPLICATE',
      priority: 100,
      title: 'This statement covers days another statement already covers',
      subject: { docIds: ['doc_copy', 'doc_feb'] },
      allowedActions: ['CONFIRM_DUPLICATE', 'NOT_DUPLICATE'],
    }),
  },
}

export const ChooseTheType: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000010',
      kind: 'CONFIRM_TYPE',
      priority: 60,
      title: 'What kind of document is IMG_4471.jpg?',
      subject: { docIds: ['doc_photo'] },
      suggestion: { docType: 'RECEIPT', confidence: '0.42' },
      allowedActions: ['SET_TYPE'],
    }),
  },
}

export const CheckAValue: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000004',
      kind: 'LOW_CONFIDENCE_VALUE',
      title: 'Check the date and total read from the receipt of 17 Feb 2026',
      subject: { receiptIds: ['rcp_17feb'], docIds: ['doc_rcp'], field: 'total' },
      allowedActions: ['ACCEPT_AS_READ'],
    }),
  },
}

export const LineACheckNames: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000005',
      kind: 'UNMATCHED_BANK_LINE',
      title: 'IDR 2,150,000.00 received on 14 Feb 2026 has no supporting document',
      subject: { bankLineIds: ['tx_14feb'], docIds: ['doc_feb'] },
      allowedActions: ['MATCH', 'NO_DOCUMENT_NEEDED', 'IGNORE'],
    }),
  },
}

/** A ledger export with a new layout: which column is which, confirmed once (spec 005, T005-11). */
export const CheckColumns: Story = {
  args: {
    item: item({
      itemId: 'itm_0000000000000004',
      kind: 'CONFIRM_LEDGER_MAPPING',
      month: null,
      docId: 'doc_gl_new',
      title: 'Check the columns of GL_2026_Q2.csv',
      subject: { docIds: ['doc_gl_new'] },
      allowedActions: ['CONFIRM_MAPPING'],
    }),
  },
}
