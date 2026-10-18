import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { seoPlugin } from './build/seoPlugin.ts'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), seoPlugin()],
  envDir: '..',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    // Form and landing tests type and animate in jsdom; under a full parallel run, or on the build
    // machine, some take longer than the default 5 s.
    testTimeout: 15_000,
    setupFiles: './src/test-setup.ts',
    // A fixed placeholder config: tests never depend on a developer's .env (Firebase refuses an
    // empty API key at import) and never reach a real project.
    env: {
      VITE_FIREBASE_API_KEY: 'test-api-key',
      VITE_FIREBASE_AUTH_DOMAIN: 'demo-kredibel.firebaseapp.com',
      VITE_FIREBASE_PROJECT_ID: 'demo-kredibel',
      VITE_FIREBASE_APP_ID: '1:000000000000:web:0000000000000000',
      VITE_FIRESTORE_DATABASE: '(default)',
    },
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
