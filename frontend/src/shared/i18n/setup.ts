import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { DEFAULT_LANGUAGE } from './languages'
import commonEn from './locales/en/common.json'

void i18n.use(initReactI18next).init({
  resources: {
    en: {
      common: commonEn,
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
