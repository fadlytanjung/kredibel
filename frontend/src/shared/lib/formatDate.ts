/**
 * Format dates according to calendar conventions.
 *
 * Normative reference: docs/09-data-model.md §1 and docs/11 §3.
 */

export function formatDate(
  dateInput: string | Date | number,
  options?: Intl.DateTimeFormatOptions,
): string {
  if (!dateInput) {
    return ''
  }

  const date = typeof dateInput === 'string' || typeof dateInput === 'number'
    ? new Date(dateInput)
    : dateInput

  if (isNaN(date.getTime())) {
    return ''
  }

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(date)
}
