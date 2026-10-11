/** Settings → Language and formats (AC-013-15): English selected, the rest coming soon; currency
 *  and date format read-only. */

import { useTranslation } from 'react-i18next'
import type { PlanCatalog } from '../entities/plan'
import type { Workspace } from '../entities/workspace'
import { formatDate } from '../shared/lib/formatDate'
import { Badge } from '../shared/ui/Badge'

export function LanguageSettings({ workspace, catalog }: { workspace: Workspace; catalog: PlanCatalog }) {
  const { t } = useTranslation('settings')

  return (
    <div className="panel panel-pad stack gap-6">
      <p className="muted">{t('language.intro')}</p>
      <fieldset className="stack gap-2">
        <legend className="label type-label mb-2">{t('language.uiLanguage')}</legend>
        {catalog.languages.map((language) => {
          const available = language.status === 'available'
          const selected = language.code === (workspace.defaultLanguage ?? 'en')
          return (
            <label
              key={language.code}
              className={`row min-h-11 ${available ? '' : 'muted'}`}
              aria-disabled={!available}
            >
              <input
                type="radio"
                name="language"
                value={language.code}
                checked={selected}
                disabled={!available}
                readOnly
              />
              <span>{language.label}</span>
              {!available && <Badge variant="outline">{t('plan.comingSoon')}</Badge>}
            </label>
          )
        })}
      </fieldset>
      <div className="form-wrap">
        <div className="form-grid">
          <div className="field">
            <span className="label">{t('language.currency')}</span>
            <span className="num">{workspace.currency}</span>
            <span className="hint">{t('language.readOnly')}</span>
          </div>
          <div className="field">
            <span className="label">{t('language.dateFormat')}</span>
            <span>{t('language.dateExample', { example: formatDate('2026-11-02') })}</span>
            <span className="hint">{t('language.readOnly')}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
