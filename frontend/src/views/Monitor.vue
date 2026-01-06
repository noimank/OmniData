<template>
  <div class="monitor-page">
    <el-row :gutter="20">
      <!-- 浏览器池状态 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>浏览器池</span>
              <el-icon color="#409eff"><Monitor /></el-icon>
            </div>
          </template>
          <div v-if="browserPool" class="stats-content">
            <div class="stat-item">
              <span class="label">实例数量</span>
              <span class="value">{{ browserPool.browser_count }}</span>
            </div>
            <div class="stat-item">
              <span class="label">初始配置</span>
              <span class="value">{{ browserPool.config.pool_initial_size }}</span>
            </div>
            <div class="stat-item">
              <span class="label">空闲超时</span>
              <span class="value">{{ browserPool.config.idle_timeout }}s</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 爬虫统计 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>爬虫统计</span>
              <el-icon color="#67c23a"><Document /></el-icon>
            </div>
          </template>
          <div v-if="spiderStats" class="stats-content">
            <div class="stat-item">
              <span class="label">总数量</span>
              <span class="value">{{ spiderStats.total_count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 系统资源 -->
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header>
            <div class="card-header">
              <span>系统资源</span>
              <el-icon color="#e6a23c"><Cpu /></el-icon>
            </div>
          </template>
          <div v-if="systemResource" class="stats-content">
            <div class="stat-item">
              <span class="label">运行时间</span>
              <span class="value">{{ formatUptime(systemResource.uptime_seconds) }}</span>
            </div>
            <div class="stat-item">
              <span class="label">内存使用</span>
              <span class="value">{{ systemResource.memory_usage_mb }} MB</span>
            </div>
            <div class="stat-item">
              <span class="label">Redis</span>
              <el-tag :type="systemResource.redis_connected ? 'success' : 'danger'" size="small">
                {{ systemResource.redis_connected ? '已连接' : '未连接' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 浏览器实例列表 -->
    <el-card class="mt-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>浏览器实例列表</span>
          <el-button type="primary" :icon="Refresh" @click="refresh" :loading="loading">
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="browserPool?.browsers || []" stripe>
        <el-table-column prop="index" label="索引" width="80" />
        <el-table-column label="空闲时间" width="150">
          <template #default="{ row }">
            {{ formatDuration(row.idle_time_seconds) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getIdleStatusType(row.idle_time_seconds)">
              {{ getIdleStatusText(row.idle_time_seconds) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="空闲进度">
          <template #default="{ row }">
            <el-progress
              :percentage="getIdleProgress(row.idle_time_seconds)"
              :color="getIdleProgressColor(row.idle_time_seconds)"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 爬虫列表 -->
    <el-card class="mt-20" v-loading="loading">
      <template #header>
        <span>爬虫列表</span>
      </template>

      <el-table :data="spiderStats?.spiders || []" stripe>
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="version" label="版本" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
import { Monitor, Document, Cpu, Refresh } from '@element-plus/icons-vue'

const monitorStore = useMonitorStore()

const browserPool = ref(monitorStore.browserPool)
const spiderStats = ref(monitorStore.spiderStats)
const systemResource = ref(monitorStore.systemResource)
const loading = ref(monitorStore.loading)

let timer: number | null = null

const refresh = async () => {
  await monitorStore.fetchAll()
  browserPool.value = monitorStore.browserPool
  spiderStats.value = monitorStore.spiderStats
  systemResource.value = monitorStore.systemResource
}

const formatUptime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  return `${hours}h ${minutes}m ${secs}s`
}

const formatDuration = (seconds: number) => {
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}m ${secs}s`
}

const getIdleStatusType = (seconds: number) => {
  if (seconds > 300) return 'warning'
  if (seconds > 120) return 'info'
  return 'success'
}

const getIdleStatusText = (seconds: number) => {
  if (seconds > 300) return '空闲'
  if (seconds > 120) return '较空闲'
  return '活跃'
}

const getIdleProgress = (seconds: number) => {
  const max = 300 // 5分钟
  return Math.min(Math.round((seconds / max) * 100), 100)
}

const getIdleProgressColor = (seconds: number) => {
  const percentage = getIdleProgress(seconds)
  if (percentage >= 80) return '#f56c6c'
  if (percentage >= 50) return '#e6a23c'
  return '#67c23a'
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

  .stats-content {
    .stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      .label {
        color: #909399;
        font-size: 14px;
      }

      .value {
        font-size: 18px;
        font-weight: 500;
        color: #303133;

        &.success {
          color: #67c23a;
        }

        &.warning {
          color: #e6a23c;
        }
      }
    }
  }

  .mt-20 {
    margin-top: 20px;
  }
}
</style>
