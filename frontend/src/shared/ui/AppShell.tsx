import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FileText,
  ArrowLeftRight,
  Inbox,
  ShieldAlert,
  Users,
  Sparkles,
  Tag,
  Activity,
  Settings as SettingsIcon,
  Upload,
  Search,
  Bell,
  MoreHorizontal,
  X,
  Building2,
  ChevronDown,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../../app/providers/useAuth'
import { useSizeClass } from '../lib/useSizeClass'
import { Button } from './Button'

export interface AppShellProps {
  children: React.ReactNode
  workspaceName?: string
  workspaceSub?: string
  unreadRiskCount?: number
  reviewCount?: number
  docCount?: number
  labelCount?: number
  trialDaysLeft?: number
  pagesRead?: number
  pagesQuota?: number
  onUpload?: () => void
}

interface NavItemDef {
  path: string
  labelLong: string
  labelShort: string
  icon: React.ComponentType<{ className?: string }>
  count?: number
  countNeutral?: boolean
  badge?: string
}

export function AppShell({
  children,
  workspaceName = 'Sunrise Coffee Roasters',
  workspaceSub = 'Company, IDR, IFRS',
  unreadRiskCount = 2,
  reviewCount = 9,
  docCount = 92,
  labelCount = 37,
  trialDaysLeft = 23,
  pagesRead = 286,
  pagesQuota = 400,
  onUpload,
}: AppShellProps) {
  const { isCompact, isLarge, isWide } = useSizeClass()
  const location = useLocation()
  const { user, signOut } = useAuth()
  const [moreSheetOpen, setMoreSheetOpen] = useState(false)

  const showSidebar = isLarge || isWide
  const showRail = !isCompact && !showSidebar

  const navItems: NavItemDef[] = [
    { path: '/', labelLong: 'Dashboard', labelShort: 'Dashboard', icon: LayoutDashboard },
    {
      path: '/documents',
      labelLong: 'Documents',
      labelShort: 'Documents',
      icon: FileText,
      count: docCount,
      countNeutral: true,
    },
    { path: '/months', labelLong: 'Reconciliation', labelShort: 'Reconcile', icon: ArrowLeftRight },
    {
      path: '/review',
      labelLong: 'Review',
      labelShort: 'Review',
      icon: Inbox,
      count: reviewCount,
    },
    {
      path: '/risk',
      labelLong: 'Risk',
      labelShort: 'Risk',
      icon: ShieldAlert,
      count: unreadRiskCount,
    },
    { path: '/counterparties', labelLong: 'Clients and suppliers', labelShort: 'Clients', icon: Users },
    { path: '/assistant', labelLong: 'Assistant', labelShort: 'Assistant', icon: Sparkles, badge: 'P1' },
    {
      path: '/labels',
      labelLong: 'Labels',
      labelShort: 'Labels',
      icon: Tag,
      count: labelCount,
      countNeutral: true,
    },
    { path: '/runs', labelLong: 'Runs', labelShort: 'Runs', icon: Activity },
  ]

  const userDisplayName = user?.displayName || user?.email?.split('@')[0] || 'Maya Sari'
  const userInitials = userDisplayName
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase()

  const currentRouteName =
    navItems.find((n) => n.path === location.pathname)?.labelLong || 'Dashboard'

  const progressPercent = Math.min(100, Math.round((pagesRead / pagesQuota) * 100))

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col medium:flex-row">
      {/* 1. Large / Wide Screen Sidebar (>= 1200px) */}
      {showSidebar && (
        <aside
          aria-label="Sidebar navigation"
          className="w-62 shrink-0 min-h-screen bg-surface border-r border-line flex flex-col p-4 gap-1 sticky top-0 h-screen overflow-y-auto"
        >
          <div className="flex items-center gap-2 px-2 py-1">
            <Link to="/" aria-label="Kredibel home">
              <img src="/brand/kredibel-logo.svg" alt="Kredibel" className="h-8 w-auto" />
            </Link>
          </div>

          {/* Workspace info */}
          <Link
            to="/settings"
            className="flex items-center gap-2.5 p-2.5 my-3 rounded-sm bg-sunken text-ink hover:bg-line transition-colors"
          >
            <div className="w-8 h-8 rounded-sm bg-surface text-brand grid place-items-center shrink-0">
              <Building2 className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <strong className="block text-sm font-semibold truncate leading-tight">
                {workspaceName}
              </strong>
              <span className="block text-xs text-ink-muted truncate">{workspaceSub}</span>
            </div>
            <ChevronDown className="w-4 h-4 text-ink-muted shrink-0" />
          </Link>

          {/* Nav groups */}
          <nav aria-label="Main navigation" className="flex flex-col gap-0.5 flex-1">
            <Link
              to="/"
              className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
                location.pathname === '/'
                  ? 'bg-brand-soft text-brand font-semibold'
                  : 'text-ink-muted hover:text-ink hover:bg-sunken'
              }`}
            >
              <LayoutDashboard className="w-5 h-5 shrink-0" />
              <span>Dashboard</span>
            </Link>

            <span className="text-xs font-semibold text-ink-subtle px-3 pt-3 pb-1">Books</span>
            {navItems.slice(1, 5).map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
                    active
                      ? 'bg-brand-soft text-brand font-semibold'
                      : 'text-ink-muted hover:text-ink hover:bg-sunken'
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  <span className="flex-1 truncate">{item.labelLong}</span>
                  {item.count !== undefined && (
                    <span
                      className={`px-1.5 py-0.5 text-xs font-bold rounded-full num ${
                        item.countNeutral
                          ? 'bg-sunken text-ink-muted'
                          : 'bg-critical text-on-brand'
                      }`}
                    >
                      {item.count}
                    </span>
                  )}
                </Link>
              )
            })}

            <span className="text-xs font-semibold text-ink-subtle px-3 pt-3 pb-1">Insight</span>
            {navItems.slice(5, 7).map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
                    active
                      ? 'bg-brand-soft text-brand font-semibold'
                      : 'text-ink-muted hover:text-ink hover:bg-sunken'
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  <span className="flex-1 truncate">{item.labelLong}</span>
                  {item.badge && (
                    <span className="px-1.5 py-0.5 text-xs font-semibold rounded-xs bg-sunken text-ink-muted">
                      {item.badge}
                    </span>
                  )}
                </Link>
              )
            })}

            <span className="text-xs font-semibold text-ink-subtle px-3 pt-3 pb-1">AI quality</span>
            {navItems.slice(7).map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium transition-colors ${
                    active
                      ? 'bg-brand-soft text-brand font-semibold'
                      : 'text-ink-muted hover:text-ink hover:bg-sunken'
                  }`}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  <span className="flex-1 truncate">{item.labelLong}</span>
                  {item.count !== undefined && (
                    <span className="px-1.5 py-0.5 text-xs font-bold rounded-full bg-sunken text-ink-muted num">
                      {item.count}
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          {/* Footer of sidebar: trial card, settings, user */}
          <div className="flex flex-col gap-2 mt-auto pt-2 border-t border-line">
            <div className="p-3 rounded-md bg-inverse text-on-inverse text-xs flex flex-col gap-1.5">
              <strong className="text-sm font-semibold">Free trial: {trialDaysLeft} days left</strong>
              <span className="text-on-inverse/80">
                {pagesRead} of {pagesQuota} pages read this month
              </span>
              <div className="h-1.5 rounded-full bg-surface/20 overflow-hidden mt-1">
                <div
                  className="h-full bg-brand-accent rounded-full transition-all"
                  style={{ width: `${progressPercent}%` }} /* allow-raw-style: computed geometry */
                />
              </div>
              <Link to="/settings" className="text-brand-accent font-semibold hover:underline mt-0.5">
                Plan and usage
              </Link>
            </div>

            <Link
              to="/settings"
              className="flex items-center gap-3 px-3 py-2 rounded-sm text-sm font-medium text-ink-muted hover:text-ink hover:bg-sunken transition-colors"
            >
              <SettingsIcon className="w-5 h-5 shrink-0" />
              <span>Settings</span>
            </Link>

            <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-sm">
              <div className="w-8 h-8 rounded-full bg-brand-soft text-brand font-bold text-xs grid place-items-center shrink-0">
                {userInitials}
              </div>
              <div className="min-w-0 flex-1">
                <strong className="block text-sm font-semibold truncate leading-tight">
                  {userDisplayName}
                </strong>
                <span className="block text-xs text-ink-muted">Owner</span>
              </div>
              <button
                type="button"
                onClick={() => signOut()}
                className="p-1 rounded-sm text-ink-muted hover:text-critical hover:bg-critical-soft transition-colors cursor-pointer"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        </aside>
      )}

      {/* 2. Medium Screen Navigation Rail (600px - 1199px) */}
      {showRail && (
        <aside
          aria-label="Rail navigation"
          className="w-22 shrink-0 min-h-screen bg-surface border-r border-line flex flex-col items-center py-4 gap-2 sticky top-0 h-screen overflow-y-auto"
        >
          <Link to="/" aria-label="Kredibel home" className="mb-2">
            <img src="/brand/kredibel-mark.svg" alt="Kredibel" className="w-10 h-10" />
          </Link>

          <nav aria-label="Rail nav" className="flex flex-col items-center gap-1 flex-1">
            {navItems.map((item, idx) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              const isSeparator = idx === 5 || idx === 7
              return (
                <React.Fragment key={item.path}>
                  {isSeparator && <div className="w-10 h-px bg-line my-1" />}
                  <Link
                    to={item.path}
                    title={item.labelLong}
                    className={`flex flex-col items-center justify-center gap-1 w-16 h-14 rounded-sm text-xs transition-colors relative ${
                      active
                        ? 'text-brand font-semibold'
                        : 'text-ink-muted hover:text-ink hover:bg-sunken'
                    }`}
                  >
                    <div
                      className={`w-10 h-7 rounded-full grid place-items-center ${
                        active ? 'bg-brand-soft text-brand' : ''
                      }`}
                    >
                      <Icon className="w-5 h-5 shrink-0" />
                    </div>
                    <span className="text-xs leading-none truncate max-w-full">
                      {item.labelShort}
                    </span>
                    {item.count !== undefined && !item.countNeutral && (
                      <span className="absolute top-1 right-2 px-1 text-xs font-bold rounded-full bg-critical text-on-brand num leading-tight">
                        {item.count}
                      </span>
                    )}
                  </Link>
                </React.Fragment>
              )
            })}
          </nav>

          <div className="flex flex-col items-center gap-2 pt-2 border-t border-line w-full">
            <Link
              to="/settings"
              title="Settings"
              className="w-10 h-10 rounded-sm grid place-items-center text-ink-muted hover:bg-sunken transition-colors"
            >
              <SettingsIcon className="w-5 h-5" />
            </Link>
            <div
              className="w-8 h-8 rounded-full bg-brand-soft text-brand font-bold text-xs grid place-items-center"
              title={userDisplayName}
            >
              {userInitials}
            </div>
          </div>
        </aside>
      )}

      {/* Main Column */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="sticky top-0 z-20 flex items-center h-14 medium:h-16 px-4 medium:px-6 bg-canvas/90 backdrop-blur-md border-b border-line gap-3">
          {isCompact ? (
            <>
              <Link to="/" aria-label="Kredibel home">
                <img src="/brand/kredibel-mark.svg" alt="Kredibel" className="w-8 h-8 shrink-0" />
              </Link>
              <span className="font-semibold text-base truncate flex-1">{currentRouteName}</span>
              <Link
                to="/risk"
                className="w-11 h-11 rounded-full grid place-items-center hover:bg-sunken text-ink transition-colors relative"
                aria-label={`Notifications, ${unreadRiskCount} new`}
              >
                <Bell className="w-5 h-5" />
                {unreadRiskCount > 0 && (
                  <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-critical ring-2 ring-canvas" />
                )}
              </Link>
            </>
          ) : (
            <>
              {/* Breadcrumbs */}
              <nav aria-label="Breadcrumbs" className="flex items-center gap-1.5 text-sm">
                <span className="font-semibold text-ink truncate">{currentRouteName}</span>
              </nav>

              <div className="ml-auto flex items-center gap-3">
                {/* Period selector */}
                <div className="inline-flex items-center gap-2 h-10 px-3.5 rounded-sm border border-line bg-surface text-sm font-semibold text-ink whitespace-nowrap">
                  <span>Jan to Jun 2026</span>
                  <ChevronDown className="w-4 h-4 text-ink-muted" />
                </div>

                {/* Search */}
                <button
                  type="button"
                  className="hidden expanded:flex items-center gap-2 w-56 h-10 px-3 rounded-sm bg-sunken text-ink-muted text-sm hover:text-ink transition-colors cursor-pointer"
                >
                  <Search className="w-4 h-4" />
                  <span>Search books</span>
                  <kbd className="ml-auto px-1.5 py-0.5 rounded text-xs bg-surface border border-line-strong text-ink-muted">
                    /
                  </kbd>
                </button>

                {/* Bell notification */}
                <Link
                  to="/risk"
                  className="w-10 h-10 rounded-full grid place-items-center hover:bg-sunken text-ink transition-colors relative"
                  aria-label={`Notifications, ${unreadRiskCount} new`}
                >
                  <Bell className="w-5 h-5" />
                  {unreadRiskCount > 0 && (
                    <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-critical ring-2 ring-canvas" />
                  )}
                </Link>

                {/* Global Upload action */}
                <Button variant="primary" size="md" onClick={onUpload}>
                  <Upload className="w-4 h-4" />
                  <span>Upload</span>
                </Button>
              </div>
            </>
          )}
        </header>

        {/* Content area */}
        <main
          id="content"
          className="flex-1 px-4 medium:px-6 large:px-8 py-5 medium:py-6 large:py-8 max-w-7xl w-full"
        >
          {children}
        </main>
      </div>

      {/* 3. Compact Screen Bottom Navigation and Dock (< 600px) */}
      {isCompact && (
        <div className="sticky bottom-0 z-30">
          {/* Floating Upload button (docked above bottom nav) */}
          <div className="absolute right-4 bottom-20 z-10">
            <Button
              variant="primary"
              size="lg"
              className="rounded-full shadow-raised px-5 h-13"
              onClick={onUpload}
            >
              <Upload className="w-5 h-5" />
              <span>Upload</span>
            </Button>
          </div>

          {/* Bottom nav 5 items */}
          <nav
            aria-label="Mobile navigation"
            className="grid grid-cols-5 p-1.5 bg-surface border-t border-line"
          >
            {[
              { path: '/', label: 'Dashboard', icon: LayoutDashboard },
              { path: '/documents', label: 'Docs', icon: FileText, count: docCount, neutral: true },
              { path: '/review', label: 'Review', icon: Inbox, count: reviewCount },
              { path: '/risk', label: 'Risk', icon: ShieldAlert, count: unreadRiskCount },
            ].map((item) => {
              const active = location.pathname === item.path
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex flex-col items-center justify-center gap-1 py-1 text-xs relative ${
                    active ? 'text-brand font-semibold' : 'text-ink-muted'
                  }`}
                >
                  <div
                    className={`w-12 h-7 rounded-full grid place-items-center ${
                      active ? 'bg-brand-soft text-brand' : ''
                    }`}
                  >
                    <Icon className="w-5 h-5 shrink-0" />
                  </div>
                  <span>{item.label}</span>
                  {item.count !== undefined && !item.neutral && (
                    <span className="absolute top-0.5 right-3 px-1 text-xs font-bold rounded-full bg-critical text-on-brand num leading-tight">
                      {item.count}
                    </span>
                  )}
                </Link>
              )
            })}

            {/* More item */}
            <button
              type="button"
              onClick={() => setMoreSheetOpen(true)}
              className="flex flex-col items-center justify-center gap-1 py-1 text-xs text-ink-muted cursor-pointer"
            >
              <div className="w-12 h-7 rounded-full grid place-items-center">
                <MoreHorizontal className="w-5 h-5 shrink-0" />
              </div>
              <span>More</span>
            </button>
          </nav>
        </div>
      )}

      {/* More Sheet modal drawer for Compact screens */}
      {isCompact && moreSheetOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end">
          <div
            className="fixed inset-0 bg-inverse/40 backdrop-blur-xs"
            onClick={() => setMoreSheetOpen(false)}
          />
          <div className="relative bg-surface rounded-t-lg shadow-overlay border-t border-line p-5 flex flex-col gap-4 z-10 max-h-screen overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <strong className="text-base font-semibold">More navigation</strong>
              <button
                type="button"
                onClick={() => setMoreSheetOpen(false)}
                className="p-1 rounded-sm text-ink-muted hover:bg-sunken cursor-pointer"
                aria-label="Close sheet"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <nav className="flex flex-col gap-1">
              {[
                { path: '/months', label: 'Reconciliation', icon: ArrowLeftRight },
                { path: '/counterparties', label: 'Clients and suppliers', icon: Users },
                { path: '/assistant', label: 'Assistant', icon: Sparkles, badge: 'P1' },
                { path: '/labels', label: 'Labels', icon: Tag, count: labelCount },
                { path: '/runs', label: 'Runs', icon: Activity },
                { path: '/settings', label: 'Plan & settings', icon: SettingsIcon },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMoreSheetOpen(false)}
                    className="flex items-center gap-3 px-3 py-3 rounded-sm text-sm font-medium text-ink hover:bg-sunken transition-colors"
                  >
                    <Icon className="w-5 h-5 text-ink-muted" />
                    <span className="flex-1">{item.label}</span>
                    {item.badge && (
                      <span className="px-1.5 py-0.5 text-xs font-semibold rounded-xs bg-sunken text-ink-muted">
                        {item.badge}
                      </span>
                    )}
                    {item.count !== undefined && (
                      <span className="px-1.5 py-0.5 text-xs font-bold rounded-full bg-sunken text-ink-muted num">
                        {item.count}
                      </span>
                    )}
                  </Link>
                )
              })}
            </nav>

            <div className="pt-3 border-t border-line flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-brand-soft text-brand font-bold text-xs grid place-items-center">
                  {userInitials}
                </div>
                <div>
                  <strong className="block text-sm font-semibold">{userDisplayName}</strong>
                  <span className="block text-xs text-ink-muted">{workspaceName}</span>
                </div>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setMoreSheetOpen(false)
                  signOut()
                }}
              >
                <LogOut className="w-4 h-4" />
                <span>Sign out</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
