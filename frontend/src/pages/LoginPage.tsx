import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../app/providers/useAuth'
import { Button } from '../shared/ui/Button'

export function LoginPage() {
  const { t } = useTranslation('common')
  const { user, needsWorkspace, signInWithEmail, signInWithGoogle } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user) {
    return <Navigate to={needsWorkspace ? '/onboarding' : '/'} replace />
  }

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await signInWithEmail(email, password)
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGoogleSubmit = async () => {
    setError(null)
    setIsSubmitting(true)
    try {
      await signInWithGoogle()
      navigate('/')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('common.error'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const fillDemoAccount = (e: React.MouseEvent) => {
    e.preventDefault()
    setEmail('owner@demo.kredibel')
    setPassword('DemoPassword123!')
  }

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-canvas">
      {/* Brand Hero Column (Matching design/mocks/onboarding.html) */}
      <section className="hidden md:flex md:w-5/12 lg:w-1/2 bg-brand text-on-brand p-8 lg:p-12 flex-col justify-between">
        <div>
          <img
            src="/brand/kredibel-logo-on-dark.svg"
            alt="Kredibel"
            className="h-10 mb-8"
          />
          <div className="space-y-6">
            <p className="text-xl lg:text-2xl font-semibold tracking-tight">
              Every number has a source.
            </p>
            <ul className="space-y-4 text-sm text-on-brand/90">
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <rect x="8" y="8" width="12" height="12" rx="2" />
                  <path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8" />
                </svg>
                <span>Send the same file twice and it is never counted twice.</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" />
                  <circle cx="12" cy="12" r="1" />
                </svg>
                <span>Every number is read twice before it counts, and you can see where it came from.</span>
              </li>
              <li className="flex items-start gap-3">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-brand-accent" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                  <path d="M4 7h11.5M12 3.5 15.5 7 12 10.5" />
                  <path d="M20 17H8.5M12 13.5 8.5 17l3.5 3.5" />
                </svg>
                <span>Months reconcile themselves, in any upload order. You only fix what is left.</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Live Ledger preview */}
        <div className="my-8 rounded-sm bg-on-brand/10 p-4 font-mono text-xs space-y-2 border border-on-brand/15">
          <div className="flex items-center justify-between text-on-brand/90">
            <span>05 Mar</span>
            <span className="truncate mx-2">TRANSFER OUT GREEN VALLEY</span>
            <span className="font-semibold text-brand-accent">32,100,000</span>
          </div>
          <div className="flex items-center justify-between text-on-brand/90">
            <span>11 Mar</span>
            <span className="truncate mx-2">TRANSFER IN DAYBREAK CAFE</span>
            <span className="font-semibold text-brand-accent">6,420,000</span>
          </div>
          <div className="flex items-center justify-between text-on-brand/70">
            <span>12 Mar</span>
            <span className="truncate mx-2">ACB_Feb_2026 (1).pdf</span>
            <span className="text-on-brand/50">copy, not read</span>
          </div>
        </div>

        <p className="text-xs text-on-brand/60">
          Synthetic data only. Kredibel never moves money and never changes your accounting system.
        </p>
      </section>

      {/* Auth Card Column */}
      <main className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md bg-surface p-8 rounded-md border border-line shadow-raised">
          <div className="mb-6">
            <img
              src="/brand/kredibel-logo.svg"
              alt="Kredibel"
              className="h-8 mb-4 md:hidden"
            />
            <h1 className="text-2xl font-bold text-ink">
              {t('auth.title')}
            </h1>
            <p className="mt-1 text-sm text-ink-muted">
              {t('auth.subtitle')}
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-xs bg-critical-soft p-3 text-xs font-medium text-critical border border-critical-line">
              {error}
            </div>
          )}

          {/* Google Sign-in */}
          <div>
            <button
              type="button"
              onClick={handleGoogleSubmit}
              disabled={isSubmitting}
              className="w-full h-11 flex items-center justify-center gap-3 rounded-xs border border-line bg-surface px-4 text-sm font-semibold text-ink shadow-xs hover:bg-sunken transition-colors disabled:opacity-50 cursor-pointer"
            >
              <img src="/brand/google.svg" alt="" className="w-5 h-5 shrink-0" />
              <span>{t('auth.signInWithGoogle')}</span>
            </button>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-line" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-surface px-3 text-ink-subtle">Or continue with email</span>
            </div>
          </div>

          {/* Email / Password Form */}
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
                className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
                placeholder="name@company.com"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="password" className="block text-xs font-semibold text-ink">
                  {t('auth.passwordLabel')}
                </label>
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              disabled={isSubmitting}
            >
              {isSubmitting ? t('auth.signingIn') : t('auth.signInButton')}
            </Button>
          </form>

          {/* Quick Demo Login Hint */}
          <div className="mt-6 p-3 rounded-xs bg-brand-soft border border-brand-line/20 text-xs">
            <p className="font-semibold text-brand mb-1">Demo Workspace Credentials</p>
            <p className="text-ink-muted mb-2">Preconfigured demo account with S1–S4 synthetic data.</p>
            <button
              type="button"
              onClick={fillDemoAccount}
              className="text-xs font-semibold text-brand hover:underline cursor-pointer"
            >
              Fill demo: owner@demo.kredibel &rarr;
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
