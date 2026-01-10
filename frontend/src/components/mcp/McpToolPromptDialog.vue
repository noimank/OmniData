<template>
  <el-dialog
    :model-value="modelValue"
    :title="`管理工具提示词 - ${tool?.tool_name || ''}`"
    width="700px"
    @update:model-value="$emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <div v-loading="loading" class="tool-prompt-dialog">
      <!-- 当前使用版本 -->
      <div class="current-version-section">
        <div class="section-title">
          <el-text tag="b">当前使用版本</el-text>
        </div>
        <div v-if="currentVersionInfo" class="current-version-card">
          <div class="version-header">
            <div class="version-name">
              {{ currentVersionInfo.version_name || '默认版本' }}
              <el-tag v-if="currentVersionInfo.is_default" size="small" type="danger" style="margin-left: 8px">
                默认
              </el-tag>
            </div>
            <div class="version-actions">
              <el-button
                v-if="currentVersionInfo.version_name"
                size="small"
                type="info"
                link
                @click="handleResetToDefault"
              >
                恢复默认
              </el-button>
              <el-button size="small" type="primary" @click="showCreateForm = true">
                新建版本
              </el-button>
            </div>
          </div>
          <div class="version-description">
            <el-text type="info" size="small">
              {{ currentVersionInfo.description || '暂无描述' }}
            </el-text>
          </div>
        </div>
        <el-empty v-else description="暂无版本信息" :image-size="60" />
      </div>

      <!-- 新建版本表单 -->
      <div v-if="showCreateForm" class="create-form-section">
        <el-divider />
        <div class="section-title">
          <el-text tag="b">新建提示词版本</el-text>
        </div>
        <el-form :model="newPromptForm" label-width="80px" label-position="left">
          <el-form-item label="版本名称">
            <el-input
              v-model="newPromptForm.version_name"
              placeholder="如：详细版、简洁版"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="newPromptForm.description"
              type="textarea"
              :rows="4"
              placeholder="输入提示词内容..."
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small" :loading="creating" @click="handleCreatePrompt">
              创建
            </el-button>
            <el-button size="small" @click="showCreateForm = false">取消</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 可用版本列表 -->
      <div class="available-versions-section">
        <el-divider />
        <div class="section-title">
          <el-text tag="b">可用版本</el-text>
        </div>
        <div v-if="availableVersions.length > 0" class="versions-list">
          <div
            v-for="version in availableVersions"
            :key="version.id"
            class="version-item"
            :class="{ 'is-current': isCurrentVersion(version) }"
          >
            <div class="version-main">
              <div class="version-info">
                <span class="version-name-text">{{ version.version_name }}</span>
                <el-tag v-if="version.is_default" size="small" type="danger">默认</el-tag>
                <el-tag v-if="isCurrentVersion(version)" size="small" type="success">当前</el-tag>
              </div>
              <el-text type="info" size="small" class="version-desc">
                {{ version.description || '暂无描述' }}
              </el-text>
            </div>
            <div class="version-actions">
              <el-button
                v-if="!isCurrentVersion(version)"
                size="small"
                type="primary"
                link
                @click="handleSelectVersion(version)"
              >
                选择
              </el-button>
              <el-button
                size="small"
                type="primary"
                link
                @click="handleEditVersion(version)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                type="danger"
                link
                :disabled="version.is_default || version.usage_count > 0"
                @click="handleDeleteVersion(version)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无可用版本" :image-size="60" />
      </div>

      <!-- 编辑版本对话框 -->
      <el-dialog
        v-model="showEditDialog"
        :title="`编辑版本 - ${editingVersion?.version_name || ''}`"
        width="500px"
        append-to-body
      >
        <el-form :model="editForm" label-width="80px">
          <el-form-item label="爬虫">
            <el-select v-model="editForm.spider_name" disabled style="width: 100%">
              <el-option
                v-for="spider in availableSpiders"
                :key="spider.name"
                :label="spider.name"
                :value="spider.name"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="版本名称">
            <el-input v-model="editForm.version_name" placeholder="版本名称" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="editForm.description"
              type="textarea"
              :rows="6"
              placeholder="输入提示词内容..."
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSaveEdit">保存</el-button>
        </template>
      </el-dialog>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMcpStore } from '@/stores/mcp'
import type { McpTool, SpiderPrompt, SpiderInfoForMcp } from '@/api/types'

interface Props {
  modelValue: boolean
  serviceId: number | null
  tool: McpTool | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  updated: []
}>()

const mcpStore = useMcpStore()

// 状态
const loading = ref(false)
const creating = ref(false)
const saving = ref(false)
const showCreateForm = ref(false)
const showEditDialog = ref(false)

// 版本信息
const currentVersionInfo = ref<{
  version_name: string | null
  description: string | null
  is_default: boolean
} | null>(null)
const availableVersions = ref<SpiderPrompt[]>([])
const availableSpiders = ref<SpiderInfoForMcp[]>([])

// 新建版本表单
const newPromptForm = ref({
  spider_name: '',
  version_name: '',
  description: '',
})

// 编辑版本表单
const editingVersion = ref<SpiderPrompt | null>(null)
const editForm = ref({
  id: 0,
  spider_name: '',
  version_name: '',
  description: '',
})

// 计算属性
const isCurrentVersion = (version: SpiderPrompt) => {
  if (!currentVersionInfo.value) return false
  return currentVersionInfo.value.version_name === version.version_name
}

// 加载版本信息
const loadVersionInfo = async () => {
  if (!props.serviceId || !props.tool) return

  loading.value = true
  try {
    // 加载工具当前版本信息
    const toolVersionInfo = await mcpStore.getToolPromptVersion(props.serviceId, props.tool.id)
    if (toolVersionInfo) {
      currentVersionInfo.value = {
        version_name: toolVersionInfo.current_version,
        description: toolVersionInfo.current_description,
        is_default: toolVersionInfo.available_versions.find(
          v => v.version_name === toolVersionInfo.current_version
        )?.is_default ?? false,
      }
    }

    // 加载爬虫的所有提示词版本
    await loadAvailableVersions()
  } catch (err: any) {
    ElMessage.error(err.message || '加载版本信息失败')
  } finally {
    loading.value = false
  }
}

// 加载可用版本列表
const loadAvailableVersions = async () => {
  if (!props.tool) return

  try {
    const prompts = await mcpStore.fetchSpiderPrompts({ spider_name: props.tool.spider_name })
    availableVersions.value = prompts
  } catch (err: any) {
    ElMessage.error(err.message || '加载可用版本失败')
  }
}

// 恢复默认版本
const handleResetToDefault = async () => {
  if (!props.serviceId || !props.tool) return

  try {
    await ElMessageBox.confirm('确定要恢复为默认版本吗？', '提示', { type: 'warning' })
  } catch {
    return
  }

  loading.value = true
  try {
    await mcpStore.clearToolPromptVersion(props.serviceId, props.tool.id)
    ElMessage.success('已恢复默认版本')
    await loadVersionInfo()
    emit('updated')
  } catch (err: any) {
    ElMessage.error(err.message || '恢复失败')
  } finally {
    loading.value = false
  }
}

// 选择版本
const handleSelectVersion = async (version: SpiderPrompt) => {
  if (!props.serviceId || !props.tool) return

  loading.value = true
  try {
    await mcpStore.setToolPromptVersion(props.serviceId, props.tool.id, {
      version_name: version.version_name,
    })
    ElMessage.success('版本设置成功')
    await loadVersionInfo()
    emit('updated')
  } catch (err: any) {
    ElMessage.error(err.message || '设置版本失败')
  } finally {
    loading.value = false
  }
}

// 创建新版本
const handleCreatePrompt = async () => {
  if (!newPromptForm.value.version_name || !newPromptForm.value.description) {
    ElMessage.warning('请填写完整信息')
    return
  }

  creating.value = true
  try {
    await mcpStore.createSpiderPrompt({
      spider_name: props.tool!.spider_name,
      version_name: newPromptForm.value.version_name,
      description: newPromptForm.value.description,
    })
    ElMessage.success('创建成功')
    showCreateForm.value = false
    newPromptForm.value = { spider_name: '', version_name: '', description: '' }
    await loadVersionInfo()
  } catch (err: any) {
    ElMessage.error(err.message || '创建失败')
  } finally {
    creating.value = false
  }
}

// 编辑版本
const handleEditVersion = (version: SpiderPrompt) => {
  editingVersion.value = version
  editForm.value = {
    id: version.id,
    spider_name: version.spider_name,
    version_name: version.version_name,
    description: version.description,
  }
  showEditDialog.value = true
}

// 保存编辑
const handleSaveEdit = async () => {
  if (!editForm.value.version_name || !editForm.value.description) {
    ElMessage.warning('请填写完整信息')
    return
  }

  saving.value = true
  try {
    await mcpStore.updateSpiderPrompt(editForm.value.id, {
      version_name: editForm.value.version_name,
      description: editForm.value.description,
    })
    ElMessage.success('保存成功')
    showEditDialog.value = false
    await loadVersionInfo()
  } catch (err: any) {
    ElMessage.error(err.message || '保存失败')
  } finally {
    saving.value = false
  }
}

// 删除版本
const handleDeleteVersion = async (version: SpiderPrompt) => {
  if (version.is_default) {
    ElMessage.warning('默认版本不可删除')
    return
  }
  if (version.usage_count > 0) {
    ElMessage.warning(`该版本被 ${version.usage_count} 个工具使用，无法删除`)
    return
  }

  try {
    await ElMessageBox.confirm('确定要删除这个版本吗？', '提示', { type: 'warning' })
  } catch {
    return
  }

  loading.value = true
  try {
    await mcpStore.deleteSpiderPrompt(version.id)
    ElMessage.success('删除成功')
    await loadVersionInfo()
  } catch (err: any) {
    ElMessage.error(err.message || '删除失败')
  } finally {
    loading.value = false
  }
}

// 关闭对话框
const handleClose = () => {
  showCreateForm.value = false
  showEditDialog.value = false
  newPromptForm.value = { spider_name: '', version_name: '', description: '' }
  emit('update:modelValue', false)
}

// 监听对话框打开
watch(() => props.modelValue, async (visible) => {
  if (visible && props.serviceId && props.tool) {
    // 初始化新建表单的爬虫名称
    newPromptForm.value.spider_name = props.tool.spider_name
    // 加载 Spider 列表
    availableSpiders.value = await mcpStore.fetchAvailableSpidersForPrompts()
    // 加载版本信息
    await loadVersionInfo()
  }
})
</script>

<style scoped lang="scss">
.tool-prompt-dialog {
  .section-title {
    margin-bottom: 12px;
  }

  // 当前版本
  .current-version-section {
    margin-bottom: 16px;

    .current-version-card {
      padding: 16px;
      background: #f5f7fa;
      border-radius: 4px;
      border-left: 3px solid var(--el-color-primary);

      .version-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;

        .version-name {
          font-size: 14px;
          font-weight: 500;
        }

        .version-actions {
          display: flex;
          gap: 8px;
        }
      }

      .version-description {
        color: var(--el-text-color-secondary);
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
        word-break: break-word;
      }
    }
  }

  // 新建表单
  .create-form-section {
    margin-bottom: 16px;
  }

  // 可用版本列表
  .available-versions-section {
    .versions-list {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .version-item {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 12px;
        background: #fff;
        border: 1px solid var(--el-border-color);
        border-radius: 4px;
        transition: all 0.2s;

        &:hover {
          border-color: var(--el-color-primary);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        &.is-current {
          border-color: var(--el-color-success);
          background: #f0f9ff;
        }

        .version-main {
          flex: 1;
          min-width: 0;

          .version-info {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;

            .version-name-text {
              font-size: 14px;
              font-weight: 500;
            }
          }

          .version-desc {
            display: block;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
          }
        }

        .version-actions {
          display: flex;
          gap: 4px;
          flex-shrink: 0;
          margin-left: 12px;
        }
      }
    }
  }
}
</style>
