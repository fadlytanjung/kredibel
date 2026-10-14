import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { Field, Input } from '../shared/ui/Field'
import { Icon } from '../shared/ui/Icon'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

/** Sign-in in the onboarding layout (there is no separate login mock): brand column and form. */
export function LoginPage() {
  const { t } = useTranslation()
  const { user, loading, needsWorkspace, signInWithEmail, signInWithGoogle } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [failed, setFailed] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Wait for /api/me before choosing between onboarding and the dashboard.
  if (user && !loading) {
    return <Navigate to={needsWorkspace ? '/onboarding' : '/dashboard'} replace />
  }

  // Firebase error text is technical and English-only; the user gets one plain message.
  const attempt = async (signIn: () => Promise<void>) => {
    setFailed(false)
    setIsSubmitting(true)
    try {
      await signIn()
      // The redirect above picks /onboarding or / once /api/me has answered.
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
    <div className="viewport">
      <div className="onboard">
        <AuthBrandPanel />
        <section className="onboard-form" aria-labelledby="login-h">
          <div className="stack gap-2">
            <h1 className="type-title" id="login-h">
              {t('auth.title')}
            </h1>
            <p className="muted">{t('auth.subtitle')}</p>
          </div>

          {failed && (
            <p role="alert" className="trial-note bg-critical-soft text-critical">
              <Icon name="circle-alert" />
              <span>{t('auth.signInFailed')}</span>
            </p>
          )}

          <button
            type="button"
            className="button button-secondary button-lg button-block"
            onClick={() => void attempt(signInWithGoogle)}
            disabled={isSubmitting}
          >
            <img src="/brand/google.svg" alt="" className="w-5 h-5" />
            {t('auth.signInWithGoogle')}
          </button>

          <p className="flex items-center gap-3 small muted" aria-hidden="true">
            <span className="flex-1 border-t border-line" />
            {t('auth.or')}
            <span className="flex-1 border-t border-line" />
          </p>

          <form className="stack gap-6" onSubmit={handleEmailSubmit}>
            <div className="form-wrap">
              <div className="form-grid">
                <Field id="email-address" className="span-2" label={t('auth.emailLabel')}>
                  <Input
                    id="email-address"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('auth.emailPlaceholder')}
                  />
                </Field>
                <Field id="password" className="span-2" label={t('auth.passwordLabel')}>
                  <Input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
              </div>
            </div>
            <button
              type="submit"
              className="button button-primary button-lg button-block"
              disabled={isSubmitting}
            >
              {isSubmitting ? t('auth.signingIn') : t('auth.signInButton')}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}
