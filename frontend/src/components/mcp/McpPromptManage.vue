<template>
  <div class="mcp-prompt-manage">
    <!-- 服务选择器 -->
    <div class="service-selector">
      <el-text>选择 MCP 服务:</el-text>
      <el-select
        v-model="selectedServiceId"
        placeholder="请选择 MCP 服务"
        style="width: 320px; margin-left: 12px"
        filterable
        @change="handleServiceChange"
      >
        <el-option
          v-for="service in activeServices"
          :key="service.id"
          :label="service.display_name"
          :value="service.id"
        >
          <div class="service-option">
            <span>{{ service.display_name }}</span>
            <el-tag size="small" type="info">{{ service.tool_count }} 工具</el-tag>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- 工具列表 -->
    <div v-if="selectedServiceId" class="tools-list-container">
      <el-table
        :data="serviceTools"
        v-loading="loadingTools"
        style="width: 100%"
        max-height="600"
        @row-click="handleManageTool"
        class="clickable-rows"
      >
        <el-table-column prop="tool_name" label="工具名称" width="200" />
        <el-table-column prop="spider_name" label="爬虫" width="180" />
        <el-table-column label="当前版本" width="150">
          <template #default="{ row }">
            <el-tag size="small" :type="row.selected_prompt_version ? 'success' : 'warning'">
              {{ row.current_prompt_version_name || '-' }}
              <el-tag v-if="!row.selected_prompt_version" size="small" type="danger" style="margin-left: 4px">
                默认
              </el-tag>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前描述" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <el-text type="info" size="small">
              {{ row.current_prompt_description || '-' }}
            </el-text>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="handleManageTool(row)">
              管理
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loadingTools && serviceTools.length === 0" description="该服务没有工具" />
    </div>

    <!-- 空状态 -->
    <el-card v-else class="empty-state">
      <el-empty description="请选择一个 MCP 服务">
        <template #image>
          <el-icon :size="80" color="#909399"><Select /></el-icon>
        </template>
      </el-empty>
    </el-card>

    <!-- 工具提示词对话框 -->
    <McpToolPromptDialog
      v-model="dialogVisible"
      :service-id="selectedServiceId"
      :tool="activeTool"
      @updated="handleDialogUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Select } from '@element-plus/icons-vue'
import { useMcpStore } from '@/stores/mcp'
import McpToolPromptDialog from './McpToolPromptDialog.vue'
import type { McpTool } from '@/api/types'

const props = defineProps<{
  initialServiceId?: number | null
}>()

const emit = defineEmits<{
  'service-id-consumed': []
}>()

const mcpStore = useMcpStore()

// 状态
const selectedServiceId = ref<number | null>(null)
const serviceTools = ref<McpTool[]>([])
const loadingTools = ref(false)
const dialogVisible = ref(false)
const activeTool = ref<McpTool | null>(null)

// 计算属性
const services = computed(() => mcpStore.services)
const activeServices = computed(() => services.value.filter((s) => s.is_active))

// 服务变更处理
const handleServiceChange = async () => {
  if (selectedServiceId.value) {
    await loadServiceTools()
  } else {
    serviceTools.value = []
  }
}

// 加载服务工具列表
const loadServiceTools = async () => {
  if (!selectedServiceId.value) return

  loadingTools.value = true
  try {
    const tools = await mcpStore.fetchServiceTools(selectedServiceId.value)
    serviceTools.value = tools || []
  } catch (err: any) {
    console.error('Failed to load service tools:', err)
    serviceTools.value = []
  } finally {
    loadingTools.value = false
  }
}

// 管理工具提示词
const handleManageTool = (tool: McpTool) => {
  activeTool.value = tool
  dialogVisible.value = true
}

// 对话框更新后刷新
const handleDialogUpdated = async () => {
  // 重新加载工具列表以更新版本信息
  await loadServiceTools()
}

// 初始化
onMounted(async () => {
  // 加载服务列表
  await mcpStore.fetchServices(true)
})

// 监听外部传入的 serviceId
watch(
  () => props.initialServiceId,
  async (newServiceId) => {
    if (newServiceId && activeServices.value.some((s) => s.id === newServiceId)) {
      selectedServiceId.value = newServiceId
      await loadServiceTools()
      emit('service-id-consumed')
    }
  },
  { immediate: true }
)
</script>

<style scoped lang="scss">
.mcp-prompt-manage {
  .service-selector {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
    padding: 16px;
    background: #f5f7fa;
    border-radius: 4px;

    .service-option {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
    }
  }

  .tools-list-container {
    :deep(.el-table) {
      border-radius: 4px;

      .el-table__body-wrapper .el-table__body tr {
        cursor: pointer;
      }
    }
  }

  .empty-state {
    :deep(.el-card__body) {
      padding: 40px 20px;
    }
  }
}
</style>
