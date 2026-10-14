/**
 * Navigation model of the app shell, as in the mocks (tools/design/mocks/shell.py, docs/11 §4.1).
 * Labels are i18n keys; counts and workspace details come from the caller, never from defaults.
 */

import type { IconName } from './icons.generated'

export type NavKey =
  | 'dashboard'
  | 'documents'
  | 'months'
  | 'review'
  | 'risk'
  | 'counterparties'
  | 'assistant'
  | 'labels'
  | 'runs'
  | 'settings'

export type NavCountKey = 'documents' | 'review' | 'risk' | 'labels'
export type NavGroup = 'main' | 'books' | 'insight' | 'ai' | 'foot'

export interface NavItem {
  key: NavKey
  path: string
  icon: IconName
  group: NavGroup
  /** Neutral counts are totals shown only in the labelled sidebar; the others are to-dos. */
  count?: { key: NavCountKey; neutral: boolean }
  /** One of the bottom navigation's four items (the fifth is More). */
  bottomNav?: boolean
  /** The floating Upload button shows on this page (hidden where it would cover the work). */
  fab?: boolean
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: 'dashboard', path: '/dashboard', icon: 'dashboard', group: 'main', bottomNav: true, fab: true },
  {
    key: 'documents',
    path: '/documents',
    icon: 'files',
    group: 'books',
    count: { key: 'documents', neutral: true },
    bottomNav: true,
    fab: true,
  },
  { key: 'months', path: '/months', icon: 'reconcile', group: 'books', fab: true },
  {
    key: 'review',
    path: '/review',
    icon: 'inbox',
    group: 'books',
    count: { key: 'review', neutral: false },
    bottomNav: true,
  },
  {
    key: 'risk',
    path: '/risk',
    icon: 'shield-alert',
    group: 'books',
    count: { key: 'risk', neutral: false },
    bottomNav: true,
    fab: true,
  },
  { key: 'counterparties', path: '/counterparties', icon: 'users', group: 'insight', fab: true },
  { key: 'assistant', path: '/assistant', icon: 'sparkles', group: 'insight' },
  {
    key: 'labels',
    path: '/labels',
    icon: 'tag',
    group: 'ai',
    count: { key: 'labels', neutral: true },
    fab: true,
  },
  { key: 'runs', path: '/runs', icon: 'flow', group: 'ai' },
  // Not drawn in the sidebar or rail: the profile row opens Settings (docs/11 §4.1); the More sheet lists it.
  { key: 'settings', path: '/settings', icon: 'sliders', group: 'foot' },
]

/** Settings sections in the order of the mock's subnav (docs/11 §6.9). */
export const SETTINGS_SECTIONS = ['profile', 'bank-accounts', 'language', 'plan', 'members'] as const
export type SettingsSection = (typeof SETTINGS_SECTIONS)[number]

export interface AppShellUser {
  name: string
  role?: string | null
}

export interface AppShellWorkspace {
  name: string
  subtitle?: string
}

export interface AppShellTrial {
  status: 'TRIALING' | 'TRIAL_EXPIRED'
  daysLeft: number
  pagesUsed: number
  pagesMax: number
}

export type AppShellCounts = Partial<Record<NavCountKey, number>>

export interface Crumb {
  /** i18n key, or literal text when `literal` is set (a month such as 2026-03). */
  label: string
  to?: string
  literal?: boolean
}

export interface PageChrome {
  item?: NavItem
  crumbs: Crumb[]
  /** Compact back button (mock: nested pages go back to the dashboard). */
  back?: { to: string; labelKey: string }
  fab: boolean
}

export function isActivePath(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`)
}

export function chromeFor(pathname: string): PageChrome {
  const item = NAV_ITEMS.find((nav) => isActivePath(pathname, nav.path))
  if (!item) return { crumbs: [], fab: false }
  const own: Crumb = { label: `nav.${item.key}.long` }

  if (item.key === 'settings') {
    const section = pathname.split('/')[2] ?? 'plan'
    return {
      item,
      crumbs: [{ label: 'nav.settings.long', to: '/settings' }, { label: `settings.sections.${section}` }],
      back: { to: '/dashboard', labelKey: 'nav.dashboard.long' },
      fab: false,
    }
  }
  const nested = pathname.slice(item.path.length).replace(/^\//, '')
  if (nested) {
    return {
      item,
      crumbs: [{ ...own, to: item.path }, { label: decodeURIComponent(nested), literal: true }],
      back: { to: item.path, labelKey: `nav.${item.key}.long` },
      fab: Boolean(item.fab),
    }
  }
  return { item, crumbs: [own], fab: Boolean(item.fab) }
}

export function initialsOf(name: string): string {
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
