import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { VitePWA } from 'vite-plugin-pwa';

// Phase 6: PWA désactivée en dev (plus de hard refresh requis).
// Phase 7: proxy WebSocket /ws → FastAPI :8000.
const API_TARGET = process.env.VITE_API_URL || 'http://localhost:8000';
const WS_TARGET  = API_TARGET.replace(/^http/, 'ws');

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: false },
      manifest: {
        name: 'Nexus9',
        short_name: 'Nexus9',
        description: 'AI Command Center',
        theme_color: '#070b11',
        background_color: '#070b11',
        display: 'standalone',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp}'],
        // Skip the multi-MB PNG fallbacks for world heroes and agent
        // avatars — modern browsers fetch the WebP via <picture> source
        // instead, and the PWA precache has a 2 MB-per-file limit anyway.
        globIgnores: ['**/world/*.png', '**/agents/*.png', '**/intro/boot.mp4'],
        navigateFallbackDenylist: [/^\/v1\//, /^\/health/, /^\/orbital/, /^\/dashboard/, /^\/ws\//],
        skipWaiting: true,
        clientsClaim: true,
      },
    }),
  ],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          react:    ['react', 'react-dom'],
          markdown: ['react-markdown', 'rehype-highlight', 'remark-gfm'],
          charts:   ['recharts'],
          router:   ['react-router'],
          three:    ['three', '@react-three/fiber', '@react-three/drei'],
          motion:   ['motion'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/v1':     API_TARGET,
      '/health': API_TARGET,
      // Phase 7 — WebSocket proxy
      '/ws':     { target: WS_TARGET, ws: true, changeOrigin: true },
    },
  },
});
