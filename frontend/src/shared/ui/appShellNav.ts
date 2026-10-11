/**
 * Navigation model of the app shell (docs/11 §4.1, AC-001-16).
 *
 * Labels are i18n keys (`nav.<key>.long` / `nav.<key>.short`); counts and workspace details come
 * from the caller, never from defaults here, so the shell cannot show numbers nobody computed.
 */

import type { ComponentType } from 'react'
import {
  ArrowLeftRight,
  FileText,
  Inbox,
  LayoutDashboard,
  Settings,
  ShieldAlert,
  Sparkles,
  Users,
} from 'lucide-react'

export type NavKey =
  | 'dashboard'
  | 'documents'
  | 'months'
  | 'review'
  | 'risk'
  | 'counterparties'
  | 'assistant'
  | 'settings'

export type NavCountKey = 'documents' | 'review' | 'risk'
export type NavGroup = 'top' | 'books' | 'insight' | 'footer'

export interface NavItem {
  key: NavKey
  path: string
  icon: ComponentType<{ className?: string }>
  group: NavGroup
  /** Neutral counts are informational; alert counts mean something waits for the user. */
  count?: { key: NavCountKey; tone: 'neutral' | 'alert' }
  /** Shown with a "Soon" badge until its P1 spec lands. */
  p1?: boolean
  /** One of the four items of the compact bottom navigation; the rest live in the More sheet. */
  bottomNav?: boolean
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: 'dashboard', path: '/', icon: LayoutDashboard, group: 'top', bottomNav: true },
  {
    key: 'documents',
    path: '/documents',
    icon: FileText,
    group: 'books',
    count: { key: 'documents', tone: 'neutral' },
    bottomNav: true,
  },
  { key: 'months', path: '/months', icon: ArrowLeftRight, group: 'books' },
  {
    key: 'review',
    path: '/review',
    icon: Inbox,
    group: 'books',
    count: { key: 'review', tone: 'alert' },
    bottomNav: true,
  },
  {
    key: 'risk',
    path: '/risk',
    icon: ShieldAlert,
    group: 'books',
    count: { key: 'risk', tone: 'alert' },
    bottomNav: true,
  },
  { key: 'counterparties', path: '/counterparties', icon: Users, group: 'insight' },
  { key: 'assistant', path: '/assistant', icon: Sparkles, group: 'insight', p1: true },
  { key: 'settings', path: '/settings', icon: Settings, group: 'footer' },
]

export interface AppShellUser {
  name: string
  role?: string | null
}

export interface AppShellWorkspace {
  name: string
  subtitle?: string
}

export interface AppShellTrial {
  daysLeft: number
  pagesUsed: number
  pagesMax: number
}

export type AppShellCounts = Partial<Record<NavCountKey, number>>

export function isActivePath(pathname: string, path: string): boolean {
  if (path === '/') return pathname === '/'
  return pathname === path || pathname.startsWith(`${path}/`)
}

export function currentNavItem(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((item) => isActivePath(pathname, item.path))
}

export function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}
