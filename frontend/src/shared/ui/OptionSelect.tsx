/**
 * Modern OptionSelect component.
 *
 * An elevated select control with custom dropdown menu, checkmarks,
 * and keyboard navigation, while retaining an accessible underlying select
 * for screen readers and automated test queries.
 */

import { useEffect, useId, useRef, useState } from 'react'
import { Icon } from './Icon'

export interface OptionItem {
  value: string
  label: string
  badge?: string
}

export interface OptionSelectProps {
  label?: string
  value: string
  onChange: (value: string) => void
  options: OptionItem[]
  placeholder?: string
  disabled?: boolean
  required?: boolean
  ariaLabel?: string
  id?: string
  className?: string
}

export function OptionSelect({
  label,
  value,
  onChange,
  options,
  placeholder = 'Select…',
  disabled = false,
  required = false,
  ariaLabel,
  id: customId,
  className = '',
}: OptionSelectProps) {
  const generatedId = useId()
  const selectId = customId || generatedId
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const selectedOption = options.find((o) => o.value === value)

  // Close when clicking outside
  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  const handleSelect = (val: string) => {
    onChange(val)
    setIsOpen(false)
  }

  return (
    <div ref={containerRef} className={`option-select-container relative ${className}`}>
      <select
        id={selectId}
        aria-label={ariaLabel || label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        required={required}
        className="sr-only"
      >
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Custom styled trigger button */}
      <button
        type="button"
        id={`${selectId}-button`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        disabled={disabled}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        className={`input flex items-center justify-between text-left cursor-pointer transition-colors ${
          disabled ? 'opacity-50 cursor-not-allowed bg-sunken' : 'hover:border-strong'
        } ${isOpen ? 'border-brand ring-1 ring-brand' : ''}`}
      >
        <span className={`truncate text-sm ${selectedOption ? 'text-ink font-medium' : 'text-muted'}`}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <Icon
          name="chevron-down"
          size="sm"
          className={`shrink-0 ml-2 text-muted transition-transform duration-150 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <ul
          role="listbox"
          aria-labelledby={`${selectId}-button`}
          className="absolute z-50 left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-md border border-line bg-surface shadow-raised p-1 m-0 list-none"
        >
          {placeholder && (
            <li
              role="option"
              aria-selected={value === ''}
              onClick={() => handleSelect('')}
              className={`flex items-center justify-between px-3 py-2 text-sm rounded cursor-pointer transition-colors ${
                value === '' ? 'bg-sunken text-muted' : 'hover:bg-sunken text-muted'
              }`}
            >
              <span>{placeholder}</span>
              {value === '' && <Icon name="check" size="sm" className="text-brand" />}
            </li>
          )}
          {options.map((opt) => {
            const isSelected = opt.value === value
            return (
              <li
                key={opt.value}
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(opt.value)}
                className={`flex items-center justify-between px-3 py-2 text-sm rounded cursor-pointer transition-colors ${
                  isSelected ? 'bg-surface-feature text-brand font-semibold' : 'hover:bg-sunken text-ink'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="truncate">{opt.label}</span>
                  {opt.badge && (
                    <span className="badge badge-outline text-2xs py-0.5">{opt.badge}</span>
                  )}
                </div>
                {isSelected && <Icon name="check" size="sm" className="text-brand shrink-0 ml-2" />}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
