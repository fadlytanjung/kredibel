import type { components } from '../../shared/api/schema'

export type Month = components['schemas']['Month'] & {
  generation?: number
  dirty?: boolean
  note?: string | null
}
export type MonthState = components['schemas']['MonthState']
