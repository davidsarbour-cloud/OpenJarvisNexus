// ESLint flat config for Nexus9 frontend (React 19 + TS + Vite).
// Scope intentionally narrow: catch real bugs (react-hooks rules,
// no-unused-vars with leading-underscore opt-out, typescript-eslint
// recommended) without enforcing style — we already lean on tsc + prettier
// elsewhere and don't want a noisy first run.

import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';

export default tseslint.config(
  {
    ignores: ['dist/**', 'node_modules/**', 'src-tauri/**', 'public/**', '*.config.{js,ts}'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2022 },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Keep the classic React-hooks rules at error level — these catch real
      // bugs (wrong hook ordering, stale deps).
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // New-in-v7 stricter rules → start as warnings so existing 30+ findings
      // become a backlog instead of a wall. Tighten later via `lint:strict`.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/refs':                'warn',
      'react-hooks/immutability':        'warn',
      'react-hooks/purity':              'warn',
      'react-hooks/use-memo':            'warn',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Fire-and-forget try/catch around localStorage etc. — allowed
      'no-empty': ['warn', { allowEmptyCatch: true }],
      // Don't lose the caught error binding when narrowing — warn for now
      'preserve-caught-error': 'off',
      '@typescript-eslint/preserve-caught-error': 'off',
      // Allow intentional unused via _-prefix
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      // We use `any` in a few force-graph callbacks; warn but don't block.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    // shadcn/ui components export both the component AND its variants
    // (cva-generated) by convention. Suppress the react-refresh warning
    // for that folder — moving the variants to a separate file would
    // break the standard shadcn import path.
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
);
