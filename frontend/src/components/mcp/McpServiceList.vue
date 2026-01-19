<template>
  <div class="mcp-service-list">
    <!-- 头部操作栏 -->
    <div class="list-header">
      <div class="header-left">
        <el-input
          v-model="searchText"
          placeholder="搜索服务名称..."
          clearable
          style="width: 300px"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px">
          <el-option label="全部" value="" />
          <el-option label="已激活" :value="true" />
          <el-option label="已停用" :value="false" />
        </el-select>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="Plus" @click="handleCreate">
          创建服务
        </el-button>
        <el-button :icon="Refresh" @click="fetchServices" :loading="loading" />
      </div>
    </div>

    <!-- 服务列表 -->
    <el-table
      :data="filteredServices"
      v-loading="loading"
      stripe
      style="width: 100%; margin-top: 16px"
    >
      <el-table-column prop="name" label="服务名称" min-width="150">
        <template #default="{ row }">
          <div class="service-name">
            <el-text tag="b">{{ row.name }}</el-text>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="连接端点" min-width="300">
        <template #default="{ row }">
          <div class="endpoint-wrapper">
            <el-text size="small" type="primary" class="endpoint-url">
              {{ frontendOrigin }}/mcp/{{ row.name }}/
            </el-text>
            <el-button
              link
              type="primary"
              :icon="CopyDocument"
              size="small"
              @click="handleCopyEndpoint(row)"
            >
              复制
            </el-button>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="display_name" label="显示名称" min-width="150" />

      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />

      <el-table-column prop="transport" label="传输协议" width="130">
        <template #default="{ row }">
          <el-tag :type="getTransportType(row.transport)" size="small">
            {{ getTransportLabel(row.transport) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="tool_count" label="工具数量" width="100" align="center">
        <template #default="{ row }">
          <el-tag type="info" size="small">{{ row.tool_count }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="is_active" label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            :loading="row._switching"
            @change="(val: boolean) => handleToggleActive(row, val)"
          />
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button link type="success" size="small" @click="handleManagePrompts(row)">
            提示词
          </el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty
      v-if="!loading && filteredServices.length === 0"
      description="暂无 MCP 服务"
      style="padding: 40px 0"
    >
      <el-button type="primary" @click="handleCreate">创建第一个服务</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import useClipboard from 'vue-clipboard3'
import { ref, computed, onMounted } from 'vue'
import { Plus, Refresh, Search, CopyDocument } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMcpStore } from '@/stores/mcp'
import type { McpService } from '@/api/types'

const emit = defineEmits<{
  edit: [service: McpService | null]
  managePrompts: [serviceId: number]
}>()

const mcpStore = useMcpStore()
const searchText = ref('')
const statusFilter = ref<boolean | string>('')
const loading = ref(false)

// 使用剪贴板 composable
const { toClipboard } = useClipboard()

// 当前前端地址
const frontendOrigin = computed(() => window.location.origin)

const services = computed(() => mcpStore.services)

const filteredServices = computed(() => {
  let result = services.value

  if (statusFilter.value !== '') {
    result = result.filter((s) => s.is_active === statusFilter.value)
  }

  if (searchText.value) {
    const keyword = searchText.value.toLowerCase()
    result = result.filter(
      (s) =>
        s.name.toLowerCase().includes(keyword) ||
        s.display_name.toLowerCase().includes(keyword) ||
        (s.description && s.description.toLowerCase().includes(keyword))
    )
  }

  return result
})

const fetchServices = async () => {
  loading.value = true
  try {
    await mcpStore.fetchServices()
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  emit('edit', null)
}

const handleEdit = (service: McpService) => {
  if (!service.is_active) {
    ElMessage.warning('请先激活服务后再进行编辑')
    return
  }
  emit('edit', service)
}

const handleManagePrompts = (service: McpService) => {
  if (!service.is_active) {
    ElMessage.warning('请先激活服务后再管理提示词')
    return
  }
  emit('managePrompts', service.id)
}

const handleDelete = async (service: McpService) => {
  try {
    await ElMessageBox.confirm(`确定要删除服务 "${service.display_name}" 吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await mcpStore.deleteService(service.id)
    ElMessage.success('删除成功')
    await fetchServices()
  } catch {
    // 用户取消
  }
}

const handleToggleActive = async (service: any, value: boolean) => {
  service._switching = true
  try {
    if (value) {
      await mcpStore.activateService(service.id)
      ElMessage.success('服务已激活')
    } else {
      await mcpStore.deactivateService(service.id)
      ElMessage.info('服务已停用')
    }
  } catch {
    service.is_active = !value // 回滚
  } finally {
    service._switching = false
  }
}

const getTransportType = (transport: string) => {
  const types: Record<string, string> = {
    http: 'info',
    'streamable-http': 'success',
    sse: 'warning',
  }
  return types[transport] || 'info'
}

const getTransportLabel = (transport: string) => {
  const labels: Record<string, string> = {
    http: 'HTTP',
    'streamable-http': '流式 HTTP',
    sse: 'SSE',
  }
  return labels[transport] || transport
}

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleCopyEndpoint = async (service: McpService) => {
  const endpoint = `${frontendOrigin.value}/mcp/${service.name}/`
  try {
    await toClipboard(endpoint)
    ElMessage.success('连接端点已复制')
  } catch (err) {
    ElMessage.error('复制失败，请手动复制')
  }
}

onMounted(() => {
  fetchServices()
})
</script>

<style scoped lang="scss">
.mcp-service-list {
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;

    .header-left {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .header-right {
      display: flex;
      gap: 12px;
    }
  }

  .service-name {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
  }

  .endpoint-wrapper {
    display: flex;
    align-items: center;
    gap: 8px;

    .endpoint-url {
      font-family: monospace;
    }
  }
}
</style>
