import { useTranslation } from 'react-i18next'
import { PageMeta } from '../../shared/ui'
import { LegalDocument } from '../../widgets/public/LegalDocument'
import { PublicShell } from '../../widgets/PublicShell'

const SECTIONS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7'] as const

/** Privacy Policy (spec 020 AC-020-7), as a reading layout with a contents rail. */
export function PrivacyPage() {
  const { t } = useTranslation('public')

  return (
    <PublicShell>
      <PageMeta title={t('meta.privacyTitle')} description={t('meta.privacyDescription')} path="/privacy" />
      <LegalDocument ns="privacy" sections={SECTIONS} crossLink={{ to: '/terms', label: t('privacy.termsLink') }} />
    </PublicShell>
  )
}
