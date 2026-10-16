/**
 * A small, safe reader of the page Markdown Kredibel writes (spec 023, AC-023-1): headings,
 * paragraphs, pipe tables, fenced code, bullet lists and rules. It returns blocks that components
 * render as elements, never as HTML: a document is adversarial input, so its text stays text.
 */

export type MdInline = { kind: 'text' | 'strong' | 'code'; text: string }

export type MdBlock =
  | { kind: 'heading'; level: number; text: string }
  | { kind: 'paragraph'; lines: string[] }
  | { kind: 'table'; header: string[]; rows: string[][] }
  | { kind: 'code'; lang?: string; text: string }
  | { kind: 'list'; items: string[] }
  | { kind: 'rule' }

const FENCE = /^```\s*([\w-]*)\s*$/
const HEADING = /^(#{1,6})\s+(.*)$/
const RULE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/
const ITEM = /^\s*[-*]\s+(.*)$/
const DIVIDER = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/

function isRow(line: string): boolean {
  return line.trim().startsWith('|')
}

/** The cells of a pipe-table row; `\|` is a pipe inside a cell. */
function cells(line: string): string[] {
  const inner = line.trim().replace(/^\|/, '').replace(/(?<!\\)\|$/, '')
  return inner.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, '|'))
}

function startsBlock(lines: string[], i: number): boolean {
  const line = lines[i]
  return (
    FENCE.test(line) ||
    HEADING.test(line) ||
    RULE.test(line) ||
    ITEM.test(line) ||
    (isRow(line) && i + 1 < lines.length && DIVIDER.test(lines[i + 1]))
  )
}

export function parseMarkdown(source: string): MdBlock[] {
  const lines = source.replace(/\r\n?/g, '\n').split('\n')
  const out: MdBlock[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) {
      i += 1
      continue
    }
    const fence = line.match(FENCE)
    if (fence) {
      const body: string[] = []
      i += 1
      while (i < lines.length && !/^```\s*$/.test(lines[i])) body.push(lines[i++])
      i += 1
      out.push(fence[1] ? { kind: 'code', lang: fence[1], text: body.join('\n') } : { kind: 'code', text: body.join('\n') })
      continue
    }
    const heading = line.match(HEADING)
    if (heading) {
      out.push({ kind: 'heading', level: heading[1].length, text: heading[2].trim() })
      i += 1
      continue
    }
    if (RULE.test(line)) {
      out.push({ kind: 'rule' })
      i += 1
      continue
    }
    if (isRow(line) && i + 1 < lines.length && DIVIDER.test(lines[i + 1])) {
      const header = cells(line)
      const rows: string[][] = []
      i += 2
      while (i < lines.length && isRow(lines[i])) rows.push(cells(lines[i++]))
      out.push({ kind: 'table', header, rows })
      continue
    }
    if (ITEM.test(line)) {
      const items: string[] = []
      while (i < lines.length && ITEM.test(lines[i])) items.push(lines[i++].match(ITEM)?.[1] ?? '')
      out.push({ kind: 'list', items })
      continue
    }
    const paragraph: string[] = []
    while (i < lines.length && lines[i].trim() && (paragraph.length === 0 || !startsBlock(lines, i))) {
      paragraph.push(lines[i++])
    }
    out.push({ kind: 'paragraph', lines: paragraph })
  }
  return out
}

/** `**strong**` and `` `code` `` inside a line; everything else is text. */
export function parseInline(text: string): MdInline[] {
  const out: MdInline[] = []
  const pattern = /\*\*([^*]+)\*\*|`([^`]+)`/g
  let last = 0
  for (const match of text.matchAll(pattern)) {
    const at = match.index ?? 0
    if (at > last) out.push({ kind: 'text', text: text.slice(last, at) })
    out.push(match[1] !== undefined ? { kind: 'strong', text: match[1] } : { kind: 'code', text: match[2] })
    last = at + match[0].length
  }
  if (last < text.length) out.push({ kind: 'text', text: text.slice(last) })
  return out
}
