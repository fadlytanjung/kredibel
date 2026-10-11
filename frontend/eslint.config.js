import js from '@eslint/js'
import boundaries from 'eslint-plugin-boundaries'
import i18next from 'eslint-plugin-i18next'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

// Feature-Sliced Design layers (docs/11 §3): a layer imports only from the layers below it.
const LAYERS = ['app', 'pages', 'widgets', 'features', 'entities', 'shared']

export default tseslint.config(
  { ignores: ['dist', 'node_modules', '**/*.d.ts', 'storybook-static', 'test-results', 'playwright-report'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        {
          allowConstantExport: true,
          allowExportNames: [
            'buttonVariants',
            'badgeVariants',
            'panelVariants',
            'skeletonVariants',
          ],
        },
      ],
    },
  },
  {
    // AC-001-14: every user-visible string comes from locales/en/*.json through useTranslation().
    files: ['src/**/*.tsx'],
    ignores: ['src/**/*.test.tsx', 'src/**/*.stories.tsx'],
    plugins: { i18next },
    rules: {
      'i18next/no-literal-string': [
        'error',
        {
          mode: 'jsx-only',
          'jsx-attributes': {
            include: ['alt', 'aria-label', 'aria-description', 'placeholder', 'title', 'label'],
          },
          callees: {
            exclude: [
              // the plugin's defaults (an explicit list replaces them)
              'i18n(ext)?',
              't',
              'require',
              'addEventListener',
              'removeEventListener',
              'postMessage',
              'getElementById',
              'dispatch',
              'commit',
              'includes',
              'indexOf',
              'endsWith',
              'startsWith',
              // react-hook-form takes field names, which are identifiers, not UI text
              'register',
              'setValue',
              'setError',
              'fieldError',
              'invalid',
            ],
          },
        },
      ],
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { boundaries },
    settings: {
      'import/resolver': { node: { extensions: ['.ts', '.tsx', '.js', '.json'] } },
      'boundaries/elements': LAYERS.map((layer) => ({ type: layer, pattern: `src/${layer}` })),
    },
    rules: {
      'boundaries/dependencies': [
        'error',
        {
          default: 'disallow',
          policies: LAYERS.map((layer, i) => ({
            from: { element: { type: layer } },
            allow: { to: { element: { types: { anyOf: LAYERS.slice(i) } } } },
          })),
        },
      ],
    },
  },
)
