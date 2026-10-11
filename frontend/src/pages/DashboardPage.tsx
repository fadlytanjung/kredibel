import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button } from '../shared/ui/Button'
import { EmptyState } from '../shared/ui/EmptyState'
import { Icon } from '../shared/ui/Icon'

/**
 * AC-001-3: a workspace without documents sees the upload empty state in the kit's page frame.
 * The status sentence, figures, lists and charts of design/mocks/dashboard.html arrive with spec
 * 010, computed from the workspace's own books.
 */
export function DashboardPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div className="page">
      <EmptyState
        icon={<Icon name="upload" size="lg" />}
        title={t('dashboard.emptyTitle')}
        description={t('dashboard.emptyDescription')}
        action={
          <Button size="lg" onClick={() => navigate('/documents?upload=1')}>
            <Icon name="upload" size="sm" />
            {t('dashboard.uploadButton')}
          </Button>
        }
      />
    </div>
  )
}
