<template>
  <div class="mcp-manage-page">
    <el-card>
      <el-tabs v-model="activeTab" type="border-card">
        <!-- 服务管理 -->
        <el-tab-pane label="服务管理" name="services">
          <McpServiceList v-if="activeTab === 'services'" @edit="handleEditService" />
        </el-tab-pane>

        <!-- 提示词管理 -->
        <el-tab-pane label="提示词管理" name="prompts">
          <McpPromptManage v-if="activeTab === 'prompts'" />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 服务编辑对话框 -->
    <McpServiceForm
      v-model="formVisible"
      :service="editingService"
      @saved="handleFormSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import McpServiceList from '@/components/mcp/McpServiceList.vue'
import McpPromptManage from '@/components/mcp/McpPromptManage.vue'
import McpServiceForm from '@/components/mcp/McpServiceForm.vue'
import type { McpService } from '@/api/types'

const activeTab = ref('services')
const formVisible = ref(false)
const editingService = ref<McpService | null>(null)

const handleEditService = (service: McpService | null) => {
  editingService.value = service
  formVisible.value = true
}

const handleFormSaved = () => {
  formVisible.value = false
  editingService.value = null
}
</script>

<style scoped lang="scss">
.mcp-manage-page {
  :deep(.el-card__body) {
    padding: 0;
  }

  :deep(.el-tabs--border-card) {
    border: none;
    box-shadow: none;
  }

  :deep(.el-tab-pane) {
    padding: 20px;
  }
}
</style>
