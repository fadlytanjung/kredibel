/**
 * Authentication provider tracking user sessions and workspace claims.
 *
 * Normative references: docs/specs/001-foundation/spec.md AC-001-3, AC-001-4, AC-001-7.
 */

import {
  browserLocalPersistence,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  type User,
} from 'firebase/auth'
import React, { useEffect, useState } from 'react'
import { apiClient, setTokenProvider, setUnauthorizedHandler } from '../../shared/api/client'
import { auth, googleAuthProvider } from '../../shared/firebase/app'
import { AuthContext, type AuthContextType, type MeResponse } from './AuthContext'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [me, setMe] = useState<MeResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchMe = async () => {
    try {
      const data = await apiClient<MeResponse>('/api/me')
      setMe(data)
    } catch {
      setMe(null)
    }
  }

  const handleSignOut = async () => {
    try {
      await firebaseSignOut(auth)
    } finally {
      setUser(null)
      setMe(null)
      setTokenProvider(null)
    }
  }

  useEffect(() => {
    setUnauthorizedHandler(handleSignOut)

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser)
      if (currentUser) {
        setTokenProvider(async () => currentUser.getIdToken())
        await fetchMe()
      } else {
        setTokenProvider(null)
        setMe(null)
      }
      setLoading(false)
    })

    return () => {
      unsubscribe()
      setUnauthorizedHandler(null)
    }
  }, [])

  const signInWithEmail = async (email: string, pass: string) => {
    await setPersistence(auth, browserLocalPersistence)
    const result = await signInWithEmailAndPassword(auth, email, pass)
    setUser(result.user)
    setTokenProvider(async () => result.user.getIdToken())
    await fetchMe()
  }

  const signInWithGoogle = async () => {
    await setPersistence(auth, browserLocalPersistence)
    const result = await signInWithPopup(auth, googleAuthProvider)
    setUser(result.user)
    setTokenProvider(async () => result.user.getIdToken())
    await fetchMe()
  }

  const value: AuthContextType = {
    user,
    me,
    loading,
    needsWorkspace: me ? me.needsWorkspace : false,
    signInWithEmail,
    signInWithGoogle,
    signOut: handleSignOut,
    refreshMe: fetchMe,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
