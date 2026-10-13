/** A few mutually exclusive choices as one control (the kit's `.seg`): views, frameworks, periods. */

export interface SegmentedOption {
  key: string
  label: string
}

export interface SegmentedControlProps {
  options: SegmentedOption[]
  value: string
  onChange: (key: string) => void
  ariaLabel: string
}

export function SegmentedControl({ options, value, onChange, ariaLabel }: SegmentedControlProps) {
  return (
    <div className="seg" role="group" aria-label={ariaLabel}>
      {options.map((option) => (
        <button key={option.key} type="button" aria-pressed={option.key === value} onClick={() => onChange(option.key)}>
          {option.label}
        </button>
      ))}
    </div>
  )
}
