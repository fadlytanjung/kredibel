import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DataTable, type DataTableColumn } from './DataTable'

interface MockTx {
  id: string
  description: string
  amount: number
  type: 'in' | 'out'
}

const mockData: MockTx[] = [
  { id: 'tx_1', description: 'Coffee at Daybreak Cafe', amount: 45000, type: 'out' },
  { id: 'tx_2', description: 'Consulting revenue from Client A', amount: 12000000, type: 'in' },
  { id: 'tx_3', description: 'Server hosting fee AWS', amount: 350000, type: 'out' },
  { id: 'tx_4', description: 'Invoice payment Client B', amount: 8500000, type: 'in' },
  { id: 'tx_5', description: 'Office supplies paper', amount: 120000, type: 'out' },
]

const columns: DataTableColumn<MockTx>[] = [
  {
    key: 'desc',
    header: 'Description',
    render: (tx) => <span>{tx.description}</span>,
    sortable: true,
    sortValue: (tx) => tx.description,
  },
  {
    key: 'amount',
    header: 'Amount',
    align: 'right',
    render: (tx) => <span>{tx.amount.toLocaleString()}</span>,
    sortable: true,
    sortValue: (tx) => tx.amount,
  },
]

describe('DataTable', () => {
  it('renders all columns, headers, and rows', () => {
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
      />,
    )

    expect(screen.getByText('Description')).toBeInTheDocument()
    expect(screen.getByText('Amount')).toBeInTheDocument()
    expect(screen.getByText('Coffee at Daybreak Cafe')).toBeInTheDocument()
    expect(screen.getByText('Consulting revenue from Client A')).toBeInTheDocument()
  })

  it('filters rows via search input', () => {
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
        searchable={true}
        searchPlaceholder="Search transactions..."
      />,
    )

    const searchInput = screen.getByPlaceholderText('Search transactions...')
    fireEvent.change(searchInput, { target: { value: 'Coffee' } })

    expect(screen.getByText('Coffee at Daybreak Cafe')).toBeInTheDocument()
    expect(screen.queryByText('Consulting revenue from Client A')).not.toBeInTheDocument()

    // Clear search
    const clearBtn = screen.getByRole('button', { name: /Clear search/i })
    fireEvent.click(clearBtn)

    expect(screen.getByText('Consulting revenue from Client A')).toBeInTheDocument()
  })

  it('filters rows via filter chips', () => {
    const filters = [
      { key: 'all', label: 'All', predicate: () => true },
      { key: 'in', label: 'Money in', predicate: (tx: MockTx) => tx.type === 'in' },
      { key: 'out', label: 'Money out', predicate: (tx: MockTx) => tx.type === 'out' },
    ]

    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
        filters={filters}
      />,
    )

    expect(screen.getByRole('button', { name: /Money in/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Money out/i })).toBeInTheDocument()

    // Click Money in
    fireEvent.click(screen.getByRole('button', { name: /Money in/i }))

    expect(screen.getByText('Consulting revenue from Client A')).toBeInTheDocument()
    expect(screen.getByText('Invoice payment Client B')).toBeInTheDocument()
    expect(screen.queryByText('Coffee at Daybreak Cafe')).not.toBeInTheDocument()
  })

  it('paginates data according to pageSize', () => {
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
        pageSize={2}
      />,
    )

    // First page shows 2 items
    expect(screen.getByText('Coffee at Daybreak Cafe')).toBeInTheDocument()
    expect(screen.getByText('Consulting revenue from Client A')).toBeInTheDocument()
    expect(screen.queryByText('Server hosting fee AWS')).not.toBeInTheDocument()

    // Next page
    const nextBtn = screen.getByRole('button', { name: /Next/i })
    fireEvent.click(nextBtn)

    expect(screen.getByText('Server hosting fee AWS')).toBeInTheDocument()
    expect(screen.getByText('Invoice payment Client B')).toBeInTheDocument()
    expect(screen.queryByText('Coffee at Daybreak Cafe')).not.toBeInTheDocument()
  })

  it('triggers onRowClick on click and Enter key', () => {
    const onRowClick = vi.fn()
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
        onRowClick={onRowClick}
      />,
    )

    const row = screen.getByText('Coffee at Daybreak Cafe').closest('tr')!
    fireEvent.click(row)
    expect(onRowClick).toHaveBeenCalledWith(mockData[0])

    fireEvent.keyDown(row, { key: 'Enter' })
    expect(onRowClick).toHaveBeenCalledTimes(2)
  })

  it('sorts columns when clicking sortable header', () => {
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
      />,
    )

    const header = screen.getByText('Description')
    fireEvent.click(header) // Ascending by description

    const rows = screen.getAllByRole('row').slice(1) // skip header
    expect(rows[0]).toHaveTextContent('Coffee at Daybreak Cafe')

    fireEvent.click(header) // Descending
    const descRows = screen.getAllByRole('row').slice(1)
    expect(descRows[0]).toHaveTextContent('Server hosting fee AWS')
  })

  it('shows empty state when no results match', () => {
    render(
      <DataTable
        data={mockData}
        columns={columns}
        getRowKey={(tx) => tx.id}
        searchable={true}
      />,
    )

    const searchInput = screen.getByRole('textbox')
    fireEvent.change(searchInput, { target: { value: 'NonExistentTransaction' } })

    expect(screen.getByText(/No items match your search or filter/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Clear filters/i })).toBeInTheDocument()
  })
})
