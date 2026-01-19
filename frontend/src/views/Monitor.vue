<template>
  <div class="monitor-page">
    <!-- 浏览器上下文池状态 -->
    <el-card class="mb-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>浏览器上下文池</span>
          <el-icon color="#409eff"><Monitor /></el-icon>
        </div>
      </template>
      <el-row :gutter="20" v-if="contextPool">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ contextPool.browser_count }}</div>
            <div class="stat-label">浏览器数量</div>
            <div class="stat-config">模式: {{ contextPool.config.headless ? '无头' : '有头' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ contextPool.context_count }} / {{ contextPool.config.max_pool_size }}</div>
            <div class="stat-label">Context 数量 / 池容量</div>
            <el-progress :percentage="contextPool.config.max_pool_size > 0 ? (contextPool.context_count / contextPool.config.max_pool_size * 100) : 0" :show-text="false" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value success">{{ (contextPool.reuse_rate * 100).toFixed(1) }}%</div>
            <div class="stat-label">复用率</div>
            <div class="stat-config">创建: {{ contextPool.total_contexts_created }} | 复用: {{ contextPool.total_contexts_reused }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ contextPool.total_contexts_closed }}</div>
            <div class="stat-label">已关闭数量</div>
            <div class="stat-config">淘汰: {{ contextPool.total_contexts_evicted }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 系统资源 -->
    <el-card class="mb-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>系统资源</span>
          <el-icon color="#f56c6c"><Cpu /></el-icon>
        </div>
      </template>
      <el-row :gutter="20" v-if="systemResource">
        <el-col :span="8">
          <div class="stat-card">
            <div class="stat-value">{{ formatUptime(systemResource.uptime_seconds) }}</div>
            <div class="stat-label">运行时间</div>
            <div class="stat-config">状态: {{ systemResource.status }}</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card">
            <div class="stat-value">{{ systemResource.memory_usage_mb }} MB</div>
            <div class="stat-label">内存使用 ({{ systemResource.memory_percent }}%)</div>
            <el-progress :percentage="systemResource.memory_percent" :show-text="false" />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-card">
            <div class="stat-value">{{ systemResource.cpu_percent }}%</div>
            <div class="stat-label">CPU 使用率</div>
            <div class="stat-config">
              <el-tag :type="systemResource.redis_connected ? 'success' : 'danger'" size="small">
                {{ systemResource.redis_connected ? 'Redis 已连接' : 'Redis 未连接' }}
              </el-tag>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- Context 列表 -->
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>Context 列表 ({{ contextList.length }})</span>
          <el-icon color="#67c23a"><List /></el-icon>
        </div>
      </template>
      <el-table :data="contextList" stripe style="width: 100%" v-if="contextList.length > 0">
        <el-table-column prop="namespace" label="命名空间" min-width="150">
          <template #default="{ row }">
            <el-tag :type="row.namespace === '(临时)' ? 'info' : 'primary'" size="small">
              {{ row.namespace }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="pages_count" label="Pages 数量" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.pages_count > 0 ? 'success' : 'info'" size="small">
              {{ row.pages_count }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="idle_time" label="空闲时间" min-width="180" align="center">
          <template #default="{ row }">
            <div class="idle-time-wrapper">
              <div class="idle-time-text">{{ formatIdleTime(row.idle_time) }}</div>
              <el-progress
                :percentage="getIdleTimePercent(row.idle_time)"
                :status="getIdleTimeStatus(row.idle_time)"
                :show-text="false"
                :stroke-width="6"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" align="center">
          <template #default="{ row }">
            {{ formatTimestamp(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_used_at" label="最后使用" width="160" align="center">
          <template #default="{ row }">
            {{ formatTimestamp(row.last_used_at) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无 Context" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
import { Monitor, Cpu, List } from '@element-plus/icons-vue'
import type { ContextInfo } from '@/api/types'

const monitorStore = useMonitorStore()

const contextPool = ref(monitorStore.contextPool)
const systemResource = ref(monitorStore.systemResource)
const contextList = ref<ContextInfo[]>(monitorStore.contextList)
const loading = ref(monitorStore.loading)

let timer: number | null = null

const refresh = async () => {
  await monitorStore.fetchAll()
  contextPool.value = monitorStore.contextPool
  systemResource.value = monitorStore.systemResource
  contextList.value = monitorStore.contextList
}

const formatUptime = (seconds: number) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) {
    return `${days}天 ${hours}小时`
  }
  if (hours > 0) {
    return `${hours}小时 ${minutes}分钟`
  }
  return `${minutes}分钟`
}

const formatIdleTime = (seconds: number) => {
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}分 ${secs}秒`
  }
  return `${Math.floor(seconds)}秒`
}

const formatTimestamp = (timestamp: number) => {
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (days > 0) {
    return `${days}天前`
  }
  if (hours > 0) {
    return `${hours}小时前`
  }
  if (minutes > 0) {
    return `${minutes}分钟前`
  }
  return '刚刚'
}

const getIdleTimePercent = (seconds: number) => {
  const idleTimeout = contextPool.value?.config.idle_timeout || 300
  return Math.min(100, Math.round((seconds / idleTimeout) * 100))
}

const getIdleTimeStatus = (seconds: number) => {
  const idleTimeout = contextPool.value?.config.idle_timeout || 300
  if (seconds >= idleTimeout * 0.8) return 'exception'
  if (seconds >= idleTimeout * 0.5) return 'warning'
  return ''
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 5000) // 每5秒刷新
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped lang="scss">
.monitor-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
  }

  .mb-20 {
    margin-bottom: 20px;
  }

  // 统计卡片
  .stat-card {
    text-align: center;
    padding: 20px;
    background: #f5f7fa;
    border-radius: 8px;

    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 8px;

      &.success {
        color: #67c23a;
      }
    }

    .stat-label {
      font-size: 14px;
      color: #606266;
      margin-bottom: 8px;
    }

    .stat-config {
      font-size: 12px;
      color: #909399;
    }
  }

  // 空闲时间进度条样式
  .idle-time-wrapper {
    .idle-time-text {
      font-size: 12px;
      color: #606266;
      margin-bottom: 4px;
    }

    :deep(.el-progress-bar__outer) {
      background-color: #e4e7ed;
    }
  }

  // 响应式
  @media (max-width: 768px) {
    .stat-card {
      margin-bottom: 12px;
    }
  }
}
</style>
