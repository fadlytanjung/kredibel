import type { User } from 'firebase/auth'
import { createContext } from 'react'
import type { components } from '../../shared/api/schema'

export type MeResponse = components['schemas']['Me']

export interface AuthContextType {
  user: User | null
  me: MeResponse | null
  loading: boolean
  needsWorkspace: boolean
  signInWithEmail: (email: string, pass: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
  refreshMe: () => Promise<void>
  /** Force a new ID token (fresh custom claims) and re-read /api/me (spec 013 edge case). */
  refreshSession: () => Promise<MeResponse | null>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)
