/**
 * Firebase Client SDK initialization.
 *
 * Normative reference: docs/16 §6.2 and docs/11 §2.
 */

import { getApp, getApps, initializeApp } from 'firebase/app'
import {
  browserLocalPersistence,
  getAuth,
  GoogleAuthProvider,
  indexedDBLocalPersistence,
  initializeAuth,
} from 'firebase/auth'
import type { Firestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'cloud-hack2skill.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'cloud-hack2skill',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:110491117045:web:d72e6e2372744a119bacbc',
}

export const firebaseApp = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig)
// No popup/redirect resolver at start-up: the sign-in iframe and gapi (about 130 KB) load only
// when someone signs in, so the first paint does not wait for them (AC-010-11).
function startAuth() {
  try {
    return initializeAuth(firebaseApp, {
      persistence: [indexedDBLocalPersistence, browserLocalPersistence],
    })
  } catch {
    return getAuth(firebaseApp) // already initialized (hot reload, tests)
  }
}
export const auth = startAuth()
// Kredibel's own database in the shared project (ADR-021), opened with the Firestore SDK the
// first time a page listens for live updates (AC-010-11).
let firestore: Promise<Firestore> | null = null
export function liveDb(): Promise<Firestore> {
  firestore ??= import('firebase/firestore').then((sdk) =>
    sdk.getFirestore(firebaseApp, import.meta.env.VITE_FIRESTORE_DATABASE || '(default)'),
  )
  return firestore
}
export const googleAuthProvider = new GoogleAuthProvider()

