/**
 * CommandPalette (`Cmd+K` or `/` in topbar; mock shell.py, docs/11 §4.1).
 *
 * Fast keyboard-navigable launcher for jumping to core sections, searching books,
 * or sending questions directly to the Finance Assistant.
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Icon, type IconName } from './Icon'

interface PaletteItem {
  id: string
  title: string
  subtitle?: string
  to: string
  icon: IconName
  badge?: string
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const { t } = useTranslation(['common', 'assistant', 'shell'])
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const staticItems: PaletteItem[] = useMemo(
    () => [
      {
        id: 'dashboard',
        title: t('common:nav.dashboard.long', { defaultValue: 'Dashboard' }),
        subtitle: t('common:search.dashboardDesc', { defaultValue: 'Overview, KPIs, and Cash Flow' }),
        to: '/dashboard',
        icon: 'dashboard',
      },
      {
        id: 'profit-loss',
        title: t('profitLoss:title', { defaultValue: 'Profit and Loss' }),
        subtitle: t('common:search.profitLossDesc', { defaultValue: 'Dynamic Sankey flow and ledger breakdown' }),
        to: '/profit-loss',
        icon: 'flow',
      },
      {
        id: 'documents',
        title: t('common:nav.documents.long', { defaultValue: 'Documents' }),
        subtitle: t('common:search.documentsDesc', { defaultValue: 'Bank statements, invoices, and receipts' }),
        to: '/documents',
        icon: 'files',
      },
      {
        id: 'review',
        title: t('common:nav.review.long', { defaultValue: 'Review Queue' }),
        subtitle: t('common:search.reviewDesc', { defaultValue: 'Exceptions, proposed matches, and duplicates' }),
        to: '/review',
        icon: 'inbox',
      },
      {
        id: 'risk',
        title: t('common:nav.risk.long', { defaultValue: 'Risk & Forensics' }),
        subtitle: t('common:search.riskDesc', { defaultValue: 'Forensic checks and tamper findings' }),
        to: '/risk',
        icon: 'shield-alert',
      },
      {
        id: 'assistant',
        title: t('common:nav.assistant.long', { defaultValue: 'Finance Assistant' }),
        subtitle: t('common:search.assistantDesc', { defaultValue: 'Grounded AI answers from your books' }),
        to: '/assistant',
        icon: 'sparkles',
      },
    ],
    [t],
  )

  const items: PaletteItem[] = useMemo(() => {
    const trimmed = query.trim()
    const filtered = staticItems.filter(
      (item) =>
        !trimmed ||
        item.title.toLowerCase().includes(trimmed.toLowerCase()) ||
        (item.subtitle && item.subtitle.toLowerCase().includes(trimmed.toLowerCase())),
    )
    if (!trimmed) return filtered
    return [
      {
        id: 'ask-assistant',
        title: `${t('common:search.askAssistant', { defaultValue: 'Ask Assistant' })}: "${trimmed}"`,
        subtitle: t('common:search.askAssistantDesc', {
          defaultValue: 'Search workspace books and answer with citations',
        }),
        to: `/assistant?q=${encodeURIComponent(trimmed)}`,
        icon: 'sparkles',
        badge: 'AI',
      },
      ...filtered,
    ]
  }, [query, staticItems, t])

  const handleClose = () => {
    setQuery('')
    setSelectedIndex(0)
    onClose()
  }

  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        handleClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((prev) => (items.length > 0 ? (prev + 1) % items.length : 0))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((prev) => (items.length > 0 ? (prev - 1 + items.length) % items.length : 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        if (items[selectedIndex]) {
          navigate(items[selectedIndex].to)
          handleClose()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, selectedIndex, items, navigate]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null

  return (
    <div className="cmd-palette-frame" onClick={handleClose} role="dialog" aria-modal="true">
      <div
        className="cmd-palette-dialog"
        onClick={(e) => e.stopPropagation()}
        role="combobox"
        aria-expanded="true"
        aria-haspopup="listbox"
      >
        <div className="cmd-palette-input-wrap">
          <Icon name="search" size="sm" className="text-muted" />
          <input
            ref={inputRef}
            autoFocus
            type="text"
            className="cmd-palette-input"
            placeholder={t('common:search.placeholder', { defaultValue: 'Search books or ask assistant...' })}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
          />
          <kbd className="kbd">ESC</kbd>
        </div>

        <div className="cmd-palette-list" role="listbox">
          {items.map((item, idx) => {
            const isSelected = idx === selectedIndex
            return (
              <button
                key={item.id}
                type="button"
                className={`cmd-palette-item ${isSelected ? 'is-selected' : ''}`}
                onMouseEnter={() => setSelectedIndex(idx)}
                onClick={() => {
                  navigate(item.to)
                  handleClose()
                }}
                role="option"
                aria-selected={isSelected}
              >
                <span className="cmd-palette-item-icon">
                  <Icon name={item.icon} size="sm" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="font-medium block truncate">{item.title}</span>
                  {item.subtitle && <span className="text-xs text-muted block truncate">{item.subtitle}</span>}
                </span>
                {item.badge && <span className="badge badge-brand text-2xs">{item.badge}</span>}
              </button>
            )
          })}
        </div>

        <div className="cmd-palette-foot">
          <span>{t('common:search.navigateHint', { defaultValue: 'Navigate with ↑ ↓ and Enter' })}</span>
          <span>{t('common:search.closeHint', { defaultValue: 'Close with ESC' })}</span>
        </div>
      </div>
    </div>
  )
}
