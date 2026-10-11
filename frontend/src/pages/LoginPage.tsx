import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { Button } from '../shared/ui/Button'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

const INPUT_CLASS =
  'w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand'

export function LoginPage() {
  const { t } = useTranslation()
  const { user, needsWorkspace, signInWithEmail, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [failed, setFailed] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user) {
    return <Navigate to={needsWorkspace ? '/onboarding' : '/'} replace />
  }

  // Firebase error text is technical and English-only; the user gets one plain message.
  const attempt = async (signIn: () => Promise<void>) => {
    setFailed(false)
    setIsSubmitting(true)
    try {
      await signIn()
      navigate('/')
    } catch {
      setFailed(true)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    void attempt(() => signInWithEmail(email, password))
  }

  return (
    <div className="min-h-screen flex flex-col expanded:flex-row bg-canvas">
      <AuthBrandPanel />

      <main className="flex-1 flex items-center justify-center p-4 medium:p-6 expanded:p-12">
        <div className="w-full max-w-md bg-surface p-8 rounded-md border border-line shadow-raised">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-ink">{t('auth.title')}</h1>
            <p className="mt-1 text-sm text-ink-muted">{t('auth.subtitle')}</p>
          </div>

          {failed && (
            <div
              role="alert"
              className="mb-6 rounded-xs bg-critical-soft p-3 text-xs font-medium text-critical border border-critical-line"
            >
              {t('auth.signInFailed')}
            </div>
          )}

          <button
            type="button"
            onClick={() => void attempt(signInWithGoogle)}
            disabled={isSubmitting}
            className="w-full h-11 flex items-center justify-center gap-3 rounded-xs border border-line bg-surface px-4 text-sm font-semibold text-ink shadow-xs hover:bg-sunken transition-colors disabled:opacity-50 cursor-pointer"
          >
            <img src="/brand/google.svg" alt="" className="w-5 h-5 shrink-0" />
            <span>{t('auth.signInWithGoogle')}</span>
          </button>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-line" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-surface px-3 text-ink-subtle">{t('auth.orWithEmail')}</span>
            </div>
          </div>

          <form className="space-y-4" onSubmit={handleEmailSubmit}>
            <div>
              <label htmlFor="email-address" className="block text-xs font-semibold text-ink mb-1">
                {t('auth.emailLabel')}
              </label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT_CLASS}
                placeholder={t('auth.emailPlaceholder')}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-semibold text-ink mb-1">
                {t('auth.passwordLabel')}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={INPUT_CLASS}
              />
            </div>

            <Button type="submit" variant="primary" size="lg" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? t('auth.signingIn') : t('auth.signInButton')}
            </Button>
          </form>
        </div>
      </main>
    </div>
  )
}
