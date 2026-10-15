import type { components } from '../../shared/api/schema'

export type Counterparty = components['schemas']['Counterparty'] & {
  sampleEvidence?: Record<string, unknown>[]
  bucket?: boolean
}
export type CounterpartyPage = components['schemas']['CounterpartyPage']
export type CounterpartyRole = components['schemas']['CounterpartyRole']
export type Suggestion = components['schemas']['Suggestion']
export type SuggestionDecision = components['schemas']['SuggestionDecision']['decision']
