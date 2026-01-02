import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 认知服务（FastAPI）：/api/v1/cognitive/* -> 8000
      '/api/v1/cognitive': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 知识库服务：单独转发 /api/knowledge/* 到 5001
      '/api/knowledge': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      // 其余 /api/* 仍转发到 memory 后端（5000）
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
