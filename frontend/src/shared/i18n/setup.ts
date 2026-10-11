import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import commonEn from './locales/en/common.json'

i18n.use(initReactI18next).init({
  resources: {
    en: {
      common: commonEn,
    },
  },
  lng: 'en',
  fallbackLng: 'en',
  defaultNS: 'common',
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
