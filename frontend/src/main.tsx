import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App';
import { initApiBase } from './lib/api';
import './index.css';

// ── Suppress connu-inoffensifs warnings ─────────────────────────
// Recharts log un warning "width(-1) height(-1)" pendant le premier
// paint dev (avant que ResizeObserver mesure le parent flex).
// Cosmetique uniquement, le chart se rend correctement apres mesure.
// THREE.Clock deprecation : noise interne react-three-fiber, hors de
// notre controle jusqu'a mise a jour upstream.
const _origWarn = console.warn;
console.warn = (...args: unknown[]) => {
  const m = typeof args[0] === 'string' ? args[0] : '';
  if (m.includes('width(-1)') && m.includes('height(-1)')) return;
  if (m.includes('THREE.Clock') && m.includes('deprecated')) return;
  _origWarn(...args);
};

function applyTheme() {
  try {
    const raw = localStorage.getItem('openjarvis-settings');
    const settings = raw ? JSON.parse(raw) : {};
    const theme = settings.theme || 'system';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  } catch { /* use system default */ }
}

applyTheme();

// Fetch the API base URL from the Tauri backend before rendering.
// This ensures JARVIS_PORT is defined in one place (the Rust backend).
// In non-Tauri environments this is a no-op.
initApiBase().finally(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ErrorBoundary>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ErrorBoundary>
    </StrictMode>,
  );
});
