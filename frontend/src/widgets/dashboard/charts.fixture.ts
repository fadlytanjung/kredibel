/** Synthetic money flow and cash flow (docs/18, "Sunrise Coffee Roasters") for tests and stories. */

const idr = (amount: string) => ({ amount, currency: 'IDR' })

export const FLOW_STATEMENT = {
  period: 'all',
  view: 'STATEMENT',
  framework: 'IFRS',
  nodes: [
    { id: 'src:client:harbor', column: 'SOURCE', label: 'Harborview Hotel Group', value: idr('331000000.00') },
    { id: 'src:client:daybreak', column: 'SOURCE', label: 'Daybreak Café', value: idr('189200000.00') },
    { id: 'acc:acb', column: 'ACCOUNT', label: 'Archipelago Commerce Bank ••••4821', value: idr('520200000.00') },
    { id: 'act:OPERATING', column: 'ACTIVITY', label: 'Operating', value: idr('430000000.00'), cashflowClass: 'OPERATING' },
    { id: 'act:FINANCING', column: 'ACTIVITY', label: 'Financing', value: idr('50700000.00'), cashflowClass: 'FINANCING' },
    { id: 'act:KEPT', column: 'ACTIVITY', label: 'Kept', value: idr('39500000.00') },
    { id: 'line:PAYROLL', column: 'LINE', label: 'Payroll', value: idr('257600000.00'), cashflowClass: 'OPERATING' },
    { id: 'line:RENT', column: 'LINE', label: 'Rent', value: idr('172400000.00'), cashflowClass: 'OPERATING' },
    { id: 'line:LOAN', column: 'LINE', label: 'Loan principal repaid', value: idr('50700000.00'), cashflowClass: 'FINANCING' },
  ],
  links: [
    { id: 'src:client:harbor>acc:acb', source: 'src:client:harbor', target: 'acc:acb', value: idr('331000000.00'), lineCount: 6 },
    { id: 'src:client:daybreak>acc:acb', source: 'src:client:daybreak', target: 'acc:acb', value: idr('189200000.00'), lineCount: 5 },
    { id: 'acc:acb>act:OPERATING', source: 'acc:acb', target: 'act:OPERATING', value: idr('430000000.00'), lineCount: 18 },
    { id: 'acc:acb>act:FINANCING', source: 'acc:acb', target: 'act:FINANCING', value: idr('50700000.00'), lineCount: 6 },
    { id: 'acc:acb>act:KEPT', source: 'acc:acb', target: 'act:KEPT', value: idr('39500000.00'), lineCount: 0 },
    { id: 'act:OPERATING>line:PAYROLL', source: 'act:OPERATING', target: 'line:PAYROLL', value: idr('257600000.00'), lineCount: 6 },
    { id: 'act:OPERATING>line:RENT', source: 'act:OPERATING', target: 'line:RENT', value: idr('172400000.00'), lineCount: 6 },
    { id: 'act:FINANCING>line:LOAN', source: 'act:FINANCING', target: 'line:LOAN', value: idr('50700000.00'), lineCount: 6 },
  ],
}

export const FLOW_PARTIES = {
  ...FLOW_STATEMENT,
  view: 'COUNTERPARTIES',
  nodes: [
    ...FLOW_STATEMENT.nodes.filter((n) => n.column === 'SOURCE' || n.column === 'ACCOUNT'),
    { id: 'use:PAYROLL', column: 'USE', label: 'Payroll', value: idr('257600000.00') },
    { id: 'use:SUPPLIERS', column: 'USE', label: 'Suppliers', value: idr('223100000.00') },
    { id: 'use:KEPT', column: 'USE', label: 'Kept in the account', value: idr('39500000.00') },
  ],
  links: [
    ...FLOW_STATEMENT.links.slice(0, 2),
    { id: 'acc:acb>use:PAYROLL', source: 'acc:acb', target: 'use:PAYROLL', value: idr('257600000.00'), lineCount: 6 },
    { id: 'acc:acb>use:SUPPLIERS', source: 'acc:acb', target: 'use:SUPPLIERS', value: idr('223100000.00'), lineCount: 12 },
    { id: 'acc:acb>use:KEPT', source: 'acc:acb', target: 'use:KEPT', value: idr('39500000.00'), lineCount: 0 },
  ],
}

export const CASH = {
  period: 'all',
  framework: 'IFRS',
  opening: idr('124850000.00'),
  closing: idr('164350000.00'),
  balanced: true,
  gaps: [],
  months: [
    { month: '2026-02', in: idr('153600000.00'), out: idr('140100000.00'), net: idr('13500000.00'), closing: idr('138350000.00'), riskLevel: 'MEDIUM' },
    { month: '2026-03', in: idr('86000000.00'), out: idr('122300000.00'), net: idr('-36300000.00'), closing: idr('102050000.00'), riskLevel: 'CRITICAL' },
    { month: '2026-04', in: idr('280600000.00'), out: idr('218300000.00'), net: idr('62300000.00'), closing: idr('164350000.00'), riskLevel: 'LOW' },
  ],
  byActivity: { OPERATING: idr('90200000.00'), INVESTING: idr('0.00'), FINANCING: idr('-50700000.00') },
  byLine: [],
}

export const LINES = {
  items: [
    { txId: 'tx_1', docId: 'doc_mar', date: '2026-03-04', month: '2026-03', description: 'TRANSFER IN HARBORVIEW HOTEL GROUP', amount: idr('48250000.00') },
    { txId: 'tx_2', docId: 'doc_apr', date: '2026-04-06', month: '2026-04', description: 'TRANSFER IN HARBORVIEW HOTEL GROUP', amount: idr('51900000.00') },
  ],
}
