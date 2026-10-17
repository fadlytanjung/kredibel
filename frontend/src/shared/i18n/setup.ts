import profitLossEn from './locales/en/profitLoss.json'
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { DEFAULT_LANGUAGE } from './languages'
import assistantEn from './locales/en/assistant.json'
import commonEn from './locales/en/common.json'
import dashboardEn from './locales/en/dashboard.json'
import documentsEn from './locales/en/documents.json'
import errorsEn from './locales/en/errors.json'
import monthsEn from './locales/en/months.json'
import onboardingEn from './locales/en/onboarding.json'
import counterpartiesEn from './locales/en/counterparties.json'
import publicEn from './locales/en/public.json'
import reviewEn from './locales/en/review.json'
import labelsEn from './locales/en/labels.json'
import riskEn from './locales/en/risk.json'
import runsEn from './locales/en/runs.json'
import settingsEn from './locales/en/settings.json'
import tourEn from './locales/en/tour.json'
import transactionsEn from './locales/en/transactions.json'

void i18n.use(initReactI18next).init({
  resources: {
    en: {
      assistant: assistantEn,
      profitLoss: profitLossEn,
      common: commonEn,
      dashboard: dashboardEn,
      documents: documentsEn,
      errors: errorsEn,
      months: monthsEn,
      onboarding: onboardingEn,
      public: publicEn,
      counterparties: counterpartiesEn,
      review: reviewEn,
      risk: riskEn,

      labels: labelsEn,

      runs: runsEn,
      transactions: transactionsEn,
      tour: tourEn,
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
