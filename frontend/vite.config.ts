import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// El backend expone /api en el mismo host (Nginx en prod). En dev, proxy a
// uvicorn (127.0.0.1:8000) para evitar CORS.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      // El destino del backend es configurable (VITE_API_TARGET); por defecto :8000.
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
