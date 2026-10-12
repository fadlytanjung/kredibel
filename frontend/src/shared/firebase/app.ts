/**
 * Firebase Client SDK initialization.
 *
 * Normative reference: docs/16 §6.2 and docs/11 §2.
 */

import { getApp, getApps, initializeApp } from 'firebase/app'
import { getAuth, GoogleAuthProvider } from 'firebase/auth'

import { getFirestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || 'cloud-hack2skill.firebaseapp.com',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || 'cloud-hack2skill',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '1:110491117045:web:d72e6e2372744a119bacbc',
}

export const firebaseApp = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig)
export const auth = getAuth(firebaseApp)
// Kredibel's own database in the shared project (ADR-021).
export const db = getFirestore(firebaseApp, import.meta.env.VITE_FIRESTORE_DATABASE || '(default)')
export const googleAuthProvider = new GoogleAuthProvider()

