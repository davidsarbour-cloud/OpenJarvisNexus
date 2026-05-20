// C:\OpenJarvisNexus\nexusx9\vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,   // false = prend 5174 si 5173 occupé
    host: 'localhost',
    open: true,          // Ouvre le navigateur automatiquement
  }
})