import { useTranslation } from 'react-i18next'
import { PageMeta } from '../../shared/ui'
import { LegalDocument } from '../../widgets/public/LegalDocument'
import { PublicShell } from '../../widgets/PublicShell'

const SECTIONS = ['s1', 's2', 's3', 's4', 's5', 's6', 's7', 's8'] as const

/** Terms of Service (spec 020 AC-020-7), as a reading layout with a contents rail. */
export function TermsPage() {
  const { t } = useTranslation('public')

  return (
    <PublicShell>
      <PageMeta title={t('meta.termsTitle')} description={t('meta.termsDescription')} />
      <LegalDocument ns="terms" sections={SECTIONS} crossLink={{ to: '/privacy', label: t('terms.privacyLink') }} />
    </PublicShell>
  )
}
