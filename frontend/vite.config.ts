import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 构建版本日期：格式 YYYY-MM-DD
const buildVersion = new Date().toISOString().slice(0, 10)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  define: {
    __BUILD_VERSION__: JSON.stringify(buildVersion),
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8380',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false
  }
})
