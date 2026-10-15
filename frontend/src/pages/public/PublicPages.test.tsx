import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextType } from '../../entities/session'
import { ContactPage } from './ContactPage'
import { FaqPage } from './FaqPage'
import { HowItWorksPage } from './HowItWorksPage'
import { LandingPage } from './LandingPage'
import { PricingPage } from './PricingPage'
import { PrivacyPage } from './PrivacyPage'
import { SecurityPage } from './SecurityPage'
import { TermsPage } from './TermsPage'

const auth = {
  user: null,
  me: null,
  loading: false,
  meError: false,
  needsWorkspace: false,
  signInWithEmail: async () => {},
  signInWithGoogle: async () => {},
  signOut: async () => {},
  refreshMe: async () => {},
  refreshSession: async () => null,
} as unknown as AuthContextType

function renderAt(ui: ReactNode, path = '/') {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('Public pages (spec 020)', () => {
  it('landing: tagline, hero CTA targets, the signature move and the live duplicate decision', async () => {
    const user = userEvent.setup()
    renderAt(<LandingPage />)
    expect(screen.getByRole('heading', { level: 1, name: /Every number has a source/i })).toBeInTheDocument()
    expect(screen.getByText(/agreed by two readings/)).toBeInTheDocument()
    const startLinks = screen.getAllByRole('link', { name: /Start free trial/i })
    expect(startLinks.some((link) => link.getAttribute('href') === '/login')).toBe(true)
    expect(screen.getByRole('link', { name: /See how it works/i })).toHaveAttribute('href', '/how-it-works')
    // The live decision is present and honest about duplicates.
    expect(screen.getAllByText('18,703,918').length).toBeGreaterThanOrEqual(1)
    await user.click(screen.getByRole('button', { name: 'Different' }))
    expect(screen.getByText('24,300,000')).toBeInTheDocument()
  })

  it('landing: the reading room tells its four chapters as headings, in order (AC-020-4)', () => {
    renderAt(<LandingPage />)
    const room = screen.getByRole('region', { name: 'Watch one month get checked.' })
    const titles = Array.from(room.querySelectorAll('.pub-chapter > h3'), (h) => h.textContent)
    expect(titles).toEqual([
      'It arrives in any order',
      'Every page is read twice',
      'Code checks it like a forensic accountant',
      'The month reconciles itself',
    ])
  })

  it('pricing: free trial available, paid tiers coming soon, no price', () => {
    renderAt(<PricingPage />)
    expect(screen.getByRole('heading', { level: 1, name: /Free while we build/i })).toBeInTheDocument()
    expect(screen.getByText('Free for 30 days')).toBeInTheDocument()
    expect(screen.getAllByText('Coming soon').length).toBeGreaterThanOrEqual(3)
    expect(screen.getAllByText('Pricing announced later').length).toBeGreaterThanOrEqual(2)
  })

  it('how it works: the seven steps and the cost note', () => {
    renderAt(<HowItWorksPage />)
    expect(screen.getByRole('heading', { level: 1, name: /From upload to a reconciled month/i })).toBeInTheDocument()
    expect(screen.getByText(/What reading costs/i)).toBeInTheDocument()
  })

  it('security: the honesty rules and links to the legal pages', () => {
    renderAt(<SecurityPage />)
    expect(screen.getByRole('heading', { level: 1, name: /Built to be checked/i })).toBeInTheDocument()
    const privacyLinks = screen.getAllByRole('link', { name: /Privacy Policy/i })
    expect(privacyLinks.some((link) => link.getAttribute('href') === '/privacy')).toBe(true)
  })

  it('faq: eight questions', () => {
    const { container } = renderAt(<FaqPage />)
    expect(screen.getByRole('heading', { level: 1, name: /Good to know/i })).toBeInTheDocument()
    expect(container.querySelectorAll('details')).toHaveLength(8)
  })

  it('contact: a real mailbox, no backend form', () => {
    renderAt(<ContactPage />)
    expect(screen.getByRole('heading', { level: 1, name: /Talk to us/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'hello@kredibel.app' })).toHaveAttribute(
      'href',
      'mailto:hello@kredibel.app',
    )
    expect(within(document.body).queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Copy address' })).toBeInTheDocument()
  })

  it('privacy and terms render with the placeholder for the legal entity', () => {
    const { unmount } = renderAt(<PrivacyPage />)
    expect(screen.getByRole('heading', { level: 1, name: 'Privacy Policy' })).toBeInTheDocument()
    unmount()
    renderAt(<TermsPage />)
    expect(screen.getByRole('heading', { level: 1, name: 'Terms of Service' })).toBeInTheDocument()
    expect(screen.getByText(/⟨legal entity⟩/)).toBeInTheDocument()
  })
})
