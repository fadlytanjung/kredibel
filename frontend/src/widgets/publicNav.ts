/** The public site's navigation (spec 018): header links, mobile menu and footer groups. */
export interface PublicNavItem {
  key: 'how' | 'security' | 'pricing' | 'faq' | 'contact'
  to: string
}

export const PUBLIC_NAV: readonly PublicNavItem[] = [
  { key: 'how', to: '/how-it-works' },
  { key: 'security', to: '/security' },
  { key: 'pricing', to: '/pricing' },
  { key: 'faq', to: '/faq' },
  { key: 'contact', to: '/contact' },
]

export const FOOTER_PRODUCT: readonly PublicNavItem[] = PUBLIC_NAV

export const FOOTER_COMPANY: readonly { key: 'contact' | 'signIn' | 'startTrial'; to: string }[] = [
  { key: 'contact', to: '/contact' },
  { key: 'signIn', to: '/login' },
  { key: 'startTrial', to: '/login' },
]

export const FOOTER_LEGAL: readonly { key: 'privacy' | 'terms'; to: string }[] = [
  { key: 'privacy', to: '/privacy' },
  { key: 'terms', to: '/terms' },
]
