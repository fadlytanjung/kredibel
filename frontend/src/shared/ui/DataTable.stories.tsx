import type { Meta, StoryObj } from '@storybook/react'
import { DataTable, type DataTableColumn } from './DataTable'

interface TransactionItem {
  id: string
  date: string
  description: string
  amount: string
  type: 'in' | 'out'
  category: string
}

const mockTransactions: TransactionItem[] = [
  { id: '1', date: '2026-03-01', description: 'Consulting services - Acme Corp', amount: '+15,000,000', type: 'in', category: 'Revenue' },
  { id: '2', date: '2026-03-02', description: 'AWS Cloud Hosting', amount: '-1,250,000', type: 'out', category: 'Infrastructure' },
  { id: '3', date: '2026-03-05', description: 'Office supplies & printing', amount: '-450,000', type: 'out', category: 'Operations' },
  { id: '4', date: '2026-03-08', description: 'Client retainer fee - Stark Ind', amount: '+25,000,000', type: 'in', category: 'Revenue' },
  { id: '5', date: '2026-03-12', description: 'Team catering lunch', amount: '-780,000', type: 'out', category: 'Meals' },
  { id: '6', date: '2026-03-15', description: 'Software license subscription', amount: '-2,100,000', type: 'out', category: 'Software' },
]

const columns: DataTableColumn<TransactionItem>[] = [
  {
    key: 'desc',
    header: 'Transaction',
    render: (item) => (
      <div>
        <strong>{item.description}</strong>
        <div className="reason">{item.date} · {item.category}</div>
      </div>
    ),
  },
  {
    key: 'amount',
    header: 'Amount (IDR)',
    align: 'right',
    render: (item) => (
      <span className={item.type === 'in' ? 'amt-in' : 'amt-out'}>
        {item.amount}
      </span>
    ),
  },
]

const meta: Meta<typeof DataTable<TransactionItem>> = {
  title: 'UI/DataTable',
  component: DataTable,
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof DataTable<TransactionItem>>

export const Default: Story = {
  args: {
    data: mockTransactions,
    columns,
    getRowKey: (item) => item.id,
    searchable: true,
    searchPlaceholder: 'Search transactions...',
    filters: [
      { key: 'all', label: 'All', predicate: () => true },
      { key: 'in', label: 'Money in', predicate: (t) => t.type === 'in' },
      { key: 'out', label: 'Money out', predicate: (t) => t.type === 'out' },
    ],
    pageSize: 4,
  },
}
