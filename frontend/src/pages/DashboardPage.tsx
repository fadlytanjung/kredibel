import { Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button } from '../shared/ui/Button'
import { EmptyState } from '../shared/ui/EmptyState'

/**
 * AC-001-3: a workspace without documents sees the upload empty state. The figures, month strip
 * and money flow arrive with spec 010, computed from the workspace's own books.
 */
export function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <EmptyState
      className="max-w-2xl mx-auto mt-8"
      icon={<Upload className="w-6 h-6 text-brand" />}
      title={t('dashboard.emptyTitle')}
      description={t('dashboard.emptyDescription')}
      action={
        <Button variant="primary" size="lg" onClick={() => navigate('/documents?upload=1')}>
          <Upload className="w-4 h-4" />
          {t('dashboard.uploadButton')}
        </Button>
      }
    />
  )
}
