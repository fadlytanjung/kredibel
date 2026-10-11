import i18n from '../i18n/setup'

/** The locale every Intl formatter uses: the active i18n language (AC-001-14). */
export function activeLocale(): string {
  return i18n.resolvedLanguage ?? i18n.language ?? 'en'
}
