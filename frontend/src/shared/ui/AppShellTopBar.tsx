import { Bell, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { Button } from './Button'

interface TopBarProps {
  compact: boolean
  title: string
  riskCount?: number
  onUpload?: () => void
}

function RiskBell({ riskCount, compact }: { riskCount?: number; compact: boolean }) {
  const { t } = useTranslation()
  const open = riskCount ?? 0
  return (
    <Link
      to="/risk"
      className={`${compact ? 'w-11 h-11' : 'w-10 h-10'} rounded-full grid place-items-center hover:bg-sunken text-ink transition-colors relative`}
      aria-label={t('shell.notifications', { count: open })}
    >
      <Bell className="w-5 h-5" />
      {open > 0 && (
        <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-critical ring-2 ring-canvas" />
      )}
    </Link>
  )
}

export function AppShellTopBar({ compact, title, riskCount, onUpload }: TopBarProps) {
  const { t } = useTranslation()

  return (
    <header className="sticky top-0 z-20 flex items-center h-14 medium:h-16 px-4 medium:px-6 bg-canvas/90 backdrop-blur-md border-b border-line gap-3">
      {compact ? (
        <>
          <Link to="/" aria-label={t('app.home')}>
            <img src="/brand/kredibel-mark.svg" alt={t('app.name')} className="w-8 h-8 shrink-0" />
          </Link>
          <span className="font-semibold text-base truncate flex-1">{title}</span>
          <RiskBell riskCount={riskCount} compact />
        </>
      ) : (
        <>
          <nav aria-label={t('nav.breadcrumbs')} className="flex items-center gap-1.5 text-sm">
            <span className="font-semibold text-ink truncate">{title}</span>
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <RiskBell riskCount={riskCount} compact={false} />
            <Button variant="primary" size="md" onClick={onUpload}>
              <Upload className="w-4 h-4" />
              <span>{t('shell.upload')}</span>
            </Button>
          </div>
        </>
      )}
    </header>
  )
}
