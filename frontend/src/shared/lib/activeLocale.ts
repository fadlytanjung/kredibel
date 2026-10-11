import i18n from '../i18n/setup'
import { INTL_LOCALE } from '../i18n/languages'

/** The locale every Intl formatter uses: the active i18n language (AC-001-14). */
export function activeLocale(): string {
  const language = i18n.resolvedLanguage ?? i18n.language ?? 'en'
  return INTL_LOCALE[language] ?? language
}
