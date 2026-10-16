/**
 * A page's Markdown in two tabs, as GitHub and Azure DevOps show it (spec 023, AC-023-1): Preview
 * renders headings, tables, lists and code as elements (never HTML from the text), Markdown shows
 * the file as stored. The tab a viewer chose is remembered on this device.
 */
import { useId, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { parseInline, parseMarkdown, type MdBlock } from '../lib/markdown'

type View = 'preview' | 'source'
const VIEWS: readonly View[] = ['preview', 'source']
const KEY = 'kredibel.markdownView'

function remembered(): View {
  try {
    return window.localStorage.getItem(KEY) === 'source' ? 'source' : 'preview'
  } catch {
    return 'preview'
  }
}

function remember(view: View) {
  try {
    window.localStorage.setItem(KEY, view)
  } catch {
    // Storage blocked (private window): the choice lasts this visit only.
  }
}

function Inline({ text }: { text: string }) {
  return (
    <>
      {parseInline(text).map((part, i) =>
        part.kind === 'strong' ? (
          <strong key={i}>{part.text}</strong>
        ) : part.kind === 'code' ? (
          <code key={i}>{part.text}</code>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  )
}

function Block({ block }: { block: MdBlock }): ReactNode {
  switch (block.kind) {
    case 'heading': {
      const Tag = (['h3', 'h4', 'h5', 'h6', 'h6', 'h6'] as const)[block.level - 1]
      return (
        <Tag className={`md-h${block.level}`}>
          <Inline text={block.text} />
        </Tag>
      )
    }
    case 'paragraph':
      return (
        <p>
          {block.lines.map((line, i) => (
            <span key={i} className="md-line">
              <Inline text={line} />
            </span>
          ))}
        </p>
      )
    case 'table':
      return (
        <div className="md-table">
          <table>
            <thead>
              <tr>
                {block.header.map((cell, i) => (
                  <th key={i} scope="col">
                    <Inline text={cell} />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>
                      <Inline text={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    case 'code':
      return <pre className="md-code">{block.text}</pre>
    case 'list':
      return (
        <ul>
          {block.items.map((item, i) => (
            <li key={i}>
              <Inline text={item} />
            </li>
          ))}
        </ul>
      )
    case 'rule':
      return <hr />
  }
}

export function MarkdownTabs({ text, name }: { text: string; name: string }) {
  const { t } = useTranslation()
  const id = useId()
  const [view, setView] = useState<View>(remembered)
  const blocks = useMemo(() => parseMarkdown(text), [text])
  const choose = (next: View) => {
    setView(next)
    remember(next)
  }
  const tab = (key: View) => (
    <button
      type="button"
      role="tab"
      id={`${id}-${key}`}
      aria-controls={`${id}-panel`}
      aria-selected={view === key}
      className="tab"
      onClick={() => choose(key)}
      key={key}
    >
      {t(`markdown.${key}`)}
    </button>
  )
  return (
    <div className="md-tabs">
      <div className="tabs" role="tablist" aria-label={t('markdown.tabsAria', { name })}>
        {VIEWS.map((key) => tab(key))}
      </div>
      {/* A scrolling region a keyboard can reach (axe scrollable-region-focusable). */}
      {view === 'preview' ? (
        <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-preview`} className="md-preview" tabIndex={0}>
          {blocks.map((block, i) => (
            <Block key={i} block={block} />
          ))}
        </div>
      ) : (
        <pre role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-source`} className="md-source" tabIndex={0}>
          {text}
        </pre>
      )}
    </div>
  )
}
