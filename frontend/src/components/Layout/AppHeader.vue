<template>
  <el-header height="60px" class="app-header">
    <div class="header-content">
      <div class="title">
        <h3>{{ currentTitle }}</h3>
        <span class="build-version">v{{ buildVersion }}</span>
      </div>
      <div class="header-actions">
        <!-- 可升级提示：远端 main 有新提交时显示 -->
        <el-tooltip v-if="hasUpdate" placement="bottom" :show-after="200">
          <template #content>
            <div class="upgrade-tooltip">
              <div class="tooltip-title">发现新版本</div>
              <div class="tooltip-message">{{ remoteVersion?.message }}</div>
              <div class="tooltip-hint">点击查看更新方式</div>
            </div>
          </template>
          <a class="action-link upgrade-link" @click="upgradeDialogVisible = true">
            <el-icon class="upgrade-icon"><Upload /></el-icon>
            <span>可升级</span>
          </a>
        </el-tooltip>
        <a href="https://github.com/noimank/OmniData" target="_blank" class="action-link github-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M512 42.666667A464.64 464.64 0 0 0 42.666667 502.186667 460.373333 460.373333 0 0 0 363.52 938.666667c23.466667 4.266667 32-9.813333 32-22.186667v-78.08c-130.56 27.733333-158.293333-61.44-158.293333-61.44a122.026667 122.026667 0 0 0-52.053334-67.413333c-42.666667-28.16 3.413333-27.733333 3.413334-27.733334a98.56 98.56 0 0 1 71.68 47.36 101.12 101.12 0 0 0 136.533333 37.973334 99.413333 99.413333 0 0 1 29.866667-61.44c-104.106667-11.52-213.333333-50.773333-213.333334-226.986667a177.066667 177.066667 0 0 1 47.36-124.16 161.28 161.28 0 0 1 4.693334-121.173333s39.68-12.373333 128 46.933333a455.68 455.68 0 0 1 234.666666 0c89.6-59.306667 128-46.933333 128-46.933333a161.28 161.28 0 0 1 4.693334 121.173333A177.066667 177.066667 0 0 1 810.666667 477.866667c0 176.64-110.08 215.466667-213.333334 226.986666a106.666667 106.666667 0 0 1 32 85.333334v125.866666c0 14.933333 8.533333 27.733333 32 22.186667A460.8 460.8 0 0 0 981.333333 502.186667 464.64 464.64 0 0 0 512 42.666667" fill="currentColor"/>
          </svg>
          <span>GitHub</span>
        </a>
        <a href="https://github.com/noimank/OmniData/issues" target="_blank" class="action-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M512 64C264.6 64 64 264.6 64 512s200.6 448 448 448 448-200.6 448-448S759.4 64 512 64zm0 820c-205.4 0-372-166.6-372-372s166.6-372 372-372 372 166.6 372 372-166.6 372-372 372z" fill="currentColor"/>
            <path d="M464 336a48 48 0 1 0 96 0 48 48 0 1 0-96 0zm72 112h-48c-4.4 0-8 3.6-8 8v272c0 4.4 3.6 8 8 8h48c4.4 0 8-3.6 8-8V456c0-4.4-3.6-8-8-8z" fill="currentColor"/>
          </svg>
          <span>Issues</span>
        </a>
        <a href="https://noimank.github.io/OmniData/" target="_blank" class="action-link">
          <svg class="icon" viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
            <path d="M832 64H192c-70.4 0-128 57.6-128 128v640c0 70.4 57.6 128 128 128h640c70.4 0 128-57.6 128-128V192c0-70.4-57.6-128-128-128zm0 768H192V192h640v640z" fill="currentColor"/>
            <path d="M288 320h448v64H288zm0 128h448v64H288zm0 128h320v64H288z" fill="currentColor"/>
          </svg>
          <span>文档</span>
        </a>
      </div>
    </div>

    <!-- 升级指引弹窗 -->
    <el-dialog v-model="upgradeDialogVisible" title="发现新版本" width="560px" align-center>
      <div v-if="remoteVersion" class="upgrade-dialog">
        <div class="commit-info">
          <div class="info-row">
            <span class="label">最新提交</span>
            <span class="value">{{ remoteVersion.message }}</span>
          </div>
          <div class="info-row">
            <span class="label">提交时间</span>
            <span class="value">{{ formatCommitDate(remoteVersion.commit_date) }}</span>
          </div>
          <div class="info-row">
            <span class="label">提交哈希</span>
            <a :href="remoteVersion.html_url" target="_blank" class="commit-link">
              {{ remoteVersion.commit_sha.slice(0, 7) }}
            </a>
          </div>
        </div>
        <el-divider content-position="left">更新方式</el-divider>
        <p class="update-tip">
          本项目通过 Docker 部署，请在服务器上依次执行以下命令拉取最新镜像并重建容器。
          数据库与日志已挂载到 <code>./data</code> 与 <code>./logs</code>，重建容器不会丢失数据。
        </p>
        <div class="command-block">
          <pre><code>{{ dockerUpdateCommand }}</code></pre>
          <el-button size="small" type="primary" plain :icon="CopyDocument" @click="copyCommand">
            复制命令
          </el-button>
        </div>
      </div>
    </el-dialog>
  </el-header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument, Upload } from '@element-plus/icons-vue'
import useClipboard from 'vue-clipboard3'
import { getRemoteVersion } from '@/api/version'
import type { RemoteVersion } from '@/api/types'

const route = useRoute()
const { toClipboard } = useClipboard()

const currentTitle = computed(() => route.meta.title as string || 'OmniData')
const buildVersion = __BUILD_VERSION__

// 版本检查：比对远端 main 最新提交时间与本地构建时间
const CHECK_INTERVAL = 3600 * 1000 // 1 小时
const remoteVersion = ref<RemoteVersion | null>(null)
const hasUpdate = ref(false)
const upgradeDialogVisible = ref(false)
let checkTimer: number | undefined

const dockerUpdateCommand = `docker pull noimankdocker/omnidata:latest && \\
docker rm -f omnidata && \\
docker run -d \\
  --name omnidata \\
  -p 80:80 \\
  -e TZ=Asia/Shanghai \\
  -v ./data:/app/data -v ./logs:/var/log/supervisor \\
  --restart unless-stopped \\
  noimankdocker/omnidata:latest`

const checkForUpdate = async () => {
  try {
    const res = await getRemoteVersion()
    const remote = res.data
    if (!remote?.commit_date) return

    remoteVersion.value = remote
    // 比对到日：远端提交日期（YYYY-MM-DD）晚于本地构建版本日期即视为有更新
    const remoteDay = remote.commit_date.slice(0, 10)
    hasUpdate.value = remoteDay > buildVersion
  } catch (error) {
    console.error('Failed to check remote version:', error)
  }
}

const formatCommitDate = (dateStr: string): string => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { hour12: false })
}

const copyCommand = async () => {
  try {
    await toClipboard(dockerUpdateCommand)
    ElMessage.success('命令已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

onMounted(() => {
  checkForUpdate()
  checkTimer = window.setInterval(checkForUpdate, CHECK_INTERVAL)
})

onUnmounted(() => {
  if (checkTimer) window.clearInterval(checkTimer)
})
</script>

<style scoped lang="scss">
.app-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;

    .title {
      display: flex;
      align-items: center;

      h3 {
        margin: 0;
        font-size: 18px;
        color: #303133;
      }

      .build-version {
        font-size: 12px;
        color: #909399;
        background: #f4f4f5;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 10px;
        vertical-align: middle;
        font-family: 'SF Mono', 'Cascadia Code', monospace;
      }
    }

    .header-actions {
      display: flex;
      gap: 24px;
      align-items: center;

      .action-link {
        display: flex;
        align-items: center;
        gap: 6px;
        color: #606266;
        text-decoration: none;
        font-size: 14px;
        transition: all 0.3s;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;

        .icon {
          width: 18px;
          height: 18px;
          fill: currentColor;
        }

        &:hover {
          color: #409eff;
          background-color: #f0f7ff;
        }

        &.github-link:hover {
          color: #24292e;
          background-color: #f6f8fa;
        }
      }

      // 可升级提示：橙色向上箭头 + 跳动动画，醒目提示有新版本
      .upgrade-link {
        color: #e6a23c;
        font-weight: 600;

        .upgrade-icon {
          width: 18px;
          height: 18px;
          fill: currentColor;
          animation: upgrade-bounce 1.4s ease-in-out infinite;
        }

        &:hover {
          color: #e6a23c;
          background-color: #fdf6ec;
        }
      }
    }
  }
}

// 向上箭头跳动动画，模拟"升级"的视觉隐喻
@keyframes upgrade-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-3px);
  }
}

.upgrade-tooltip {
  max-width: 280px;

  .tooltip-title {
    font-weight: 600;
    margin-bottom: 6px;
  }

  .tooltip-message {
    font-size: 13px;
    line-height: 1.5;
    word-break: break-all;
  }

  .tooltip-hint {
    margin-top: 6px;
    font-size: 12px;
    opacity: 0.8;
  }
}

.upgrade-dialog {
  .commit-info {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 14px 16px;

    .info-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 4px 0;

      .label {
        flex-shrink: 0;
        width: 60px;
        color: #909399;
        font-size: 13px;
      }

      .value {
        color: #303133;
        font-size: 13px;
        word-break: break-all;
      }

      .commit-link {
        color: #409eff;
        text-decoration: none;
        font-family: 'SF Mono', 'Cascadia Code', monospace;
        font-size: 13px;

        &:hover {
          text-decoration: underline;
        }
      }
    }
  }

  .update-tip {
    margin: 0 0 12px;
    font-size: 13px;
    color: #606266;
    line-height: 1.6;

    code {
      background: #f0f2f5;
      color: #e6a23c;
      padding: 1px 5px;
      border-radius: 3px;
      font-family: 'SF Mono', 'Cascadia Code', monospace;
      font-size: 12px;
    }
  }

  .command-block {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: #1e1e1e;
    border-radius: 8px;
    padding: 12px 16px;

    pre {
      margin: 0;
      flex: 1;
      overflow-x: auto;

      code {
        color: #d4d4d4;
        font-family: 'SF Mono', 'Cascadia Code', monospace;
        font-size: 12.5px;
        white-space: pre;
        line-height: 1.6;
      }
    }
  }
}
</style>
