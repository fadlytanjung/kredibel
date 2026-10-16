/** Whole amounts as typed (separators allowed) to the API's decimal string; empty is unknown. */
export function amountOf(text: string): string | null | undefined {
  const digits = text.replace(/[\s.,]/g, '')
  if (!digits) return null
  return /^\d{1,15}$/.test(digits) ? `${digits}.00` : undefined
}
