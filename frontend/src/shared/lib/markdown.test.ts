import { describe, expect, it } from 'vitest'
import { parseInline, parseMarkdown } from './markdown'

const PAGE = [
  '# statement-2026-03.pdf, page 1 of 2',
  'Document type: BANK_STATEMENT (0.98)',
  'Reading: AI_TEXT_LAYER, agreement 1.00',
  '',
  '## Values',
  '',
  '| Record | Field | Readings | Model | Text layer |',
  '|---|---|---|---|---|',
  '| Row 1 | description | agreed | TRANSFER A\\|B | TRANSFER A\\|B |',
  '| Row 1 | amount | agreed | 7,250,000.00 | 7,250,000.00 |',
  '',
  '## Witness text',
  '',
  '```text',
  '05/03 SETORAN | 1,000.00',
  '```',
  '',
  '---',
  '',
  '- one',
  '- two',
].join('\n')

describe('parseMarkdown (spec 023, AC-023-1)', () => {
  it('reads the page Markdown Kredibel writes into blocks', () => {
    const blocks = parseMarkdown(PAGE)
    expect(blocks.map((b) => b.kind)).toEqual(['heading', 'paragraph', 'heading', 'table', 'heading', 'code', 'rule', 'list'])
    expect(blocks[0]).toEqual({ kind: 'heading', level: 1, text: 'statement-2026-03.pdf, page 1 of 2' })
    expect(blocks[1]).toEqual({ kind: 'paragraph', lines: ['Document type: BANK_STATEMENT (0.98)', 'Reading: AI_TEXT_LAYER, agreement 1.00'] })
    const table = blocks[3]
    expect(table.kind === 'table' && table.header).toEqual(['Record', 'Field', 'Readings', 'Model', 'Text layer'])
    expect(table.kind === 'table' && table.rows[0][3]).toBe('TRANSFER A|B')
    expect(blocks[5]).toEqual({ kind: 'code', lang: 'text', text: '05/03 SETORAN | 1,000.00' })
    expect(blocks[7]).toEqual({ kind: 'list', items: ['one', 'two'] })
  })

  it('keeps markup in a document as text', () => {
    const [block] = parseMarkdown('<img src=x onerror=alert(1)> **bold** `code`')
    expect(block).toEqual({ kind: 'paragraph', lines: ['<img src=x onerror=alert(1)> **bold** `code`'] })
    expect(parseInline('a **b** `c`')).toEqual([
      { kind: 'text', text: 'a ' },
      { kind: 'strong', text: 'b' },
      { kind: 'text', text: ' ' },
      { kind: 'code', text: 'c' },
    ])
  })
})
