/** IANA time zones with their current offset, as the mock labels them: "Asia/Jakarta (UTC+7)". */

export interface TimeZoneOption {
  zone: string
  offset: string
}

function offsetOf(zone: string, at: Date): string {
  const name = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'shortOffset' })
    .formatToParts(at)
    .find((part) => part.type === 'timeZoneName')?.value
  return !name || name === 'GMT' ? 'UTC' : name.replace('GMT', 'UTC')
}

export function timeZoneOptions(at: Date = new Date()): { options: TimeZoneOption[]; current: string } {
  const current = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Jakarta'
  const zones = Intl.supportedValuesOf('timeZone')
  const all = zones.includes(current) ? zones : [current, ...zones]
  return { options: all.map((zone) => ({ zone, offset: offsetOf(zone, at) })), current }
}
