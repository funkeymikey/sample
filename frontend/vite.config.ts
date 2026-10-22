import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// The dev server proxies /api to Django, so the browser sees one origin and
// the backend needs no CORS setup. Docker Compose overrides the target.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Fail if 5173 is taken instead of silently moving to another port.
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': apiTarget,
    },
  },
})
