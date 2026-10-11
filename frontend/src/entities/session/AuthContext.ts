import type { User } from 'firebase/auth'
import { createContext } from 'react'

export interface MeResponse {
  uid: string
  email: string | null
  displayName: string | null
  orgId: string | null
  role: string | null
  needsWorkspace: boolean
  language: string
}

export interface AuthContextType {
  user: User | null
  me: MeResponse | null
  loading: boolean
  needsWorkspace: boolean
  signInWithEmail: (email: string, pass: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
  refreshMe: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)
