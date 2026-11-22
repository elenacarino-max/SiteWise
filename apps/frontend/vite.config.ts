import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'SITEWISE_')
  const proxy = {
    '/api': {
      target: env.SITEWISE_API_TARGET || 'http://127.0.0.1:8000',
      changeOrigin: true,
      rewrite: (ruta: string) => ruta.replace(/^\/api(?=\/|$)/, ''),
    },
  }

  return {
    plugins: [react()],
    server: { proxy },
    preview: { proxy },
  }
})
