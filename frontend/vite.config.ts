import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { execSync } from 'child_process'

// 构建版本号：优先取最近一次 git commit 的日期（YYYY-MM-DD），
// 失败时回退到构建机器时间，保证版本号随每次代码变更更新
function getBuildVersion() {
  try {
    // 从任意子目录向上定位到 git 仓库根目录，避免在 Docker 容器内
    // 因 WORKDIR 不在仓库根而找不到 .git
    const repoRoot = execSync('git rev-parse --show-toplevel', {
      stdio: ['ignore', 'pipe', 'ignore'],
    })
      .toString()
      .trim()
    const date = execSync(
      `git -C "${repoRoot}" log -1 --format=%cd --date=short`,
      { stdio: ['ignore', 'pipe', 'ignore'] }
    )
      .toString()
      .trim()
    if (date) return date
  } catch {
    // git 不可用时回退到当前时间
  }
  return new Date().toISOString().slice(0, 10)
}

const buildVersion = getBuildVersion()

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
