/** aria props that connect a control to its Field's error line. */
export function fieldErrorProps(id: string, error?: string) {
  return {
    'aria-invalid': error ? true : undefined,
    'aria-describedby': error ? `${id}-error` : undefined,
  }
}
