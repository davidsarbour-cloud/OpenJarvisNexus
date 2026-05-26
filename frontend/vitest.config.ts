/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import path from 'path';

// Separate vitest config so the main vite.config.ts stays focused on the app
// build (no test-runner concerns leaking into the prod bundle).
export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Default reporter is fine; CI later can override with --reporter=verbose
  },
});
