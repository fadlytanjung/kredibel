import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { DEFAULT_LANGUAGE } from './languages'
import commonEn from './locales/en/common.json'
import documentsEn from './locales/en/documents.json'
import errorsEn from './locales/en/errors.json'
import monthsEn from './locales/en/months.json'
import onboardingEn from './locales/en/onboarding.json'
import settingsEn from './locales/en/settings.json'

void i18n.use(initReactI18next).init({
  resources: {
    en: {
      common: commonEn,
      documents: documentsEn,
      errors: errorsEn,
      months: monthsEn,
      onboarding: onboardingEn,
      settings: settingsEn,
    },
  },
  lng: DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  defaultNS: 'common',
  interpolation: {
    // React already escapes rendered text.
    escapeValue: false,
  },
})

export default i18n
