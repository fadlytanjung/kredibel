/**
 * UI languages the SPA ships resources for (docs/11 §10). English is the only selectable one;
 * the full catalogue with coming-soon languages comes from GET /api/plans (spec 013).
 */
export const SUPPORTED_LANGUAGES = ['en'] as const
export type UiLanguage = (typeof SUPPORTED_LANGUAGES)[number]
export const DEFAULT_LANGUAGE: UiLanguage = 'en'

/** Intl locale per UI language. English is written day before month ("2 Nov 2026"), as in the
 *  mocks and in Indonesia; plain "en" would give "Nov 2, 2026". */
export const INTL_LOCALE: Record<string, string> = { en: 'en-GB' }
