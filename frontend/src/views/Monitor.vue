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
            <div class="stat-config">无头模式: {{ contextPool.config.headless ? '是' : '否' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ contextPool.context_count }}</div>
            <div class="stat-label">Context 数量</div>
            <div class="stat-config">已借出: {{ contextPool.checked_out_contexts }}</div>
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

    <!-- Context 统计详情 -->
    <el-card class="mb-20" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>Context 统计</span>
          <el-icon color="#67c23a"><Connection /></el-icon>
        </div>
      </template>
      <el-row :gutter="20" v-if="contextPool">
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-title">生命周期</div>
            <div class="metric-item">
              <span class="metric-label">累计创建</span>
              <span class="metric-value">{{ contextPool.total_contexts_created }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">累计复用</span>
              <span class="metric-value success">{{ contextPool.total_contexts_reused }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">累计关闭</span>
              <span class="metric-value">{{ contextPool.total_contexts_closed }}</span>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-title">复用效率</div>
            <div class="metric-item">
              <span class="metric-label">复用率</span>
              <span class="metric-value success">{{ (contextPool.reuse_rate * 100).toFixed(1) }}%</span>
            </div>
            <el-progress :percentage="contextPool.reuse_rate * 100" :show-text="false" />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-title">淘汰统计</div>
            <div class="metric-item">
              <span class="metric-label">LRU 淘汰</span>
              <span class="metric-value warning">{{ contextPool.total_contexts_evicted }}</span>
            </div>
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
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ formatUptime(systemResource.uptime_seconds) }}</div>
            <div class="stat-label">运行时间</div>
            <div class="stat-config">状态: {{ systemResource.status }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ systemResource.memory_usage_mb }} MB</div>
            <div class="stat-label">内存使用</div>
            <el-progress :percentage="systemResource.memory_percent" :show-text="false" />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ systemResource.cpu_percent }}%</div>
            <div class="stat-label">CPU 使用率</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card">
            <el-tag :type="systemResource.redis_connected ? 'success' : 'danger'" size="large">
              {{ systemResource.redis_connected ? 'Redis 已连接' : 'Redis 未连接' }}
            </el-tag>
            <div class="stat-label mt-10">缓存服务</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 配置信息 -->
    <el-card v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>配置信息</span>
          <el-icon color="#909399"><Setting /></el-icon>
        </div>
      </template>
      <el-descriptions :column="2" border v-if="contextPool">
        <el-descriptions-item label="浏览器无头模式">
          <el-tag :type="contextPool.config.headless ? 'success' : 'info'" size="small">
            {{ contextPool.config.headless ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Context 池最大容量">{{ contextPool.config.max_pool_size }}</el-descriptions-item>
        <el-descriptions-item label="Context 空闲超时">{{ formatSeconds(contextPool.config.idle_timeout) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useMonitorStore } from '@/stores/monitor'
import { Monitor, Connection, Cpu, Setting } from '@element-plus/icons-vue'

const monitorStore = useMonitorStore()

const contextPool = ref(monitorStore.contextPool)
const systemResource = ref(monitorStore.systemResource)
const loading = ref(monitorStore.loading)

let timer: number | null = null

const refresh = async () => {
  await monitorStore.fetchAll()
  contextPool.value = monitorStore.contextPool
  systemResource.value = monitorStore.systemResource
}

const formatUptime = (seconds: number) => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) {
    return `${days}天 ${hours}小时`
  }
  return `${hours}小时 ${minutes}分钟`
}

const formatSeconds = (seconds: number) => {
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return `${hours}小时 ${mins}分钟`
  }
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60)
    return `${mins}分钟`
  }
  return `${seconds}秒`
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

  .mt-10 {
    margin-top: 10px;
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

  // 指标卡片
  .metric-card {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 16px;

    .metric-title {
      font-size: 16px;
      font-weight: 500;
      color: #303133;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e4e7ed;
    }

    .metric-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;

      .metric-label {
        font-size: 14px;
        color: #606266;
      }

      .metric-value {
        font-size: 16px;
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

  // 响应式
  @media (max-width: 768px) {
    .stat-card {
      margin-bottom: 12px;
    }

    .metric-card {
      margin-bottom: 12px;
    }
  }
}
</style>
