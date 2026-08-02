import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { execSync } from 'child_process'

// 构建版本号：取构建所基于的 main 分支提交日期（YYYY-MM-DD），用于
// 1) 头部显示版本 2) 与远端最新提交日期比对，判断是否有新版本可升级。
// 优先级：CI 注入的 BUILD_DATE（Docker 构建时由 GitHub Actions 传入 main 最新提交时间戳）
// → git commit 日期 → 当前日期（兜底）
function getBuildVersion() {
  // CI 通过 --build-arg BUILD_DATE 注入 main 最新提交时间戳
  const buildDate = process.env.BUILD_DATE
  if (buildDate) {
    const date = buildDate.slice(0, 10)
    if (date) return date
  }

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
