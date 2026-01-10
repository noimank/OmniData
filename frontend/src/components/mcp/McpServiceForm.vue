<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑 MCP 服务' : '创建 MCP 服务'"
    width="700px"
    @close="handleClose"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="100px"
      v-loading="loading"
    >
      <el-form-item label="服务名称" prop="name">
        <el-input
          v-model="formData.name"
          placeholder="用于路由，如: my-service"
          :disabled="isEdit"
        />
        <div class="form-tip">服务名称将用于 MCP 路由: /mcp/{{ formData.name || '...' }}</div>
      </el-form-item>

      <el-form-item label="显示名称" prop="display_name">
        <el-input v-model="formData.display_name" placeholder="如: 我的爬虫服务" />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="服务的简要描述"
        />
      </el-form-item>

      <el-form-item label="传输协议" prop="transport">
        <el-radio-group v-model="formData.transport">
          <el-radio value="http">HTTP</el-radio>
          <el-radio value="streamable-http">流式 HTTP</el-radio>
          <el-radio value="sse">SSE</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="选择 Spider" prop="tools">
        <div class="tools-selector">
          <div class="selector-header">
            <div class="selector-left">
              <el-select
                v-model="selectedPlatform"
                placeholder="全部平台"
                clearable
                style="width: 120px"
                @change="handlePlatformChange"
              >
                <el-option label="全部平台" value="" />
                <el-option
                  v-for="platform in platforms"
                  :key="platform"
                  :label="platform"
                  :value="platform"
                />
              </el-select>
            </div>
            <div class="selector-right">
              <el-input
                v-model="spiderSearch"
                placeholder="搜索 Spider..."
                clearable
                style="width: 200px"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-text type="info">已选择: {{ formData.tools.length }} 个</el-text>
            </div>
          </div>

          <div class="spider-list">
            <el-checkbox-group v-model="selectedSpiderNames">
              <div
                v-for="spider in filteredSpiders"
                :key="spider.name"
                class="spider-item"
              >
                <el-checkbox :value="spider.name">
                  <div class="spider-info">
                    <div class="spider-name">
                      <el-text tag="b">{{ spider.name }}</el-text>
                      <el-tag size="small" type="info" style="margin-left: 8px">
                        {{ spider.platform }}
                      </el-tag>
                    </div>
                    <div class="spider-desc">{{ spider.description }}</div>
                    <div v-if="spider.parameter_info.length > 0" class="spider-params">
                      <el-text size="small" type="info">
                        参数: {{ spider.parameter_info.map((p) => p.name).join(', ') }}
                      </el-text>
                    </div>
                  </div>
                </el-checkbox>
              </div>
            </el-checkbox-group>

            <el-empty
              v-if="filteredSpiders.length === 0"
              description="没有找到 Spider"
              :image-size="80"
            />
          </div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useMcpStore } from '@/stores/mcp'
import type { McpService, McpServiceCreate } from '@/api/types'

interface Props {
  modelValue: boolean
  service: McpService | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const mcpStore = useMcpStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)
const spiderSearch = ref('')
const selectedPlatform = ref<string>('')
const selectedSpiderNames = ref<string[]>([])

const isEdit = computed(() => props.service !== null)

const formData = ref<McpServiceCreate>({
  name: '',
  display_name: '',
  description: '',
  transport: 'http',
  tools: [],
})

// 获取唯一平台列表
const platforms = computed(() => {
  const platformSet = new Set(availableSpiders.value.map((s) => s.platform))
  return Array.from(platformSet).sort()
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入服务名称', trigger: 'blur' },
    {
      pattern: /^[a-z0-9-]+$/,
      message: '只能包含小写字母、数字和连字符',
      trigger: 'blur',
    },
  ],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  transport: [{ required: true, message: '请选择传输协议', trigger: 'change' }],
}

const availableSpiders = computed(() => mcpStore.availableSpiders)

const filteredSpiders = computed(() => {
  let result = availableSpiders.value

  // 平台过滤
  if (selectedPlatform.value) {
    result = result.filter((s) => s.platform === selectedPlatform.value)
  }

  // 搜索过滤
  if (spiderSearch.value) {
    const keyword = spiderSearch.value.toLowerCase()
    result = result.filter(
      (s) =>
        s.name.toLowerCase().includes(keyword) ||
        s.description.toLowerCase().includes(keyword) ||
        s.platform.toLowerCase().includes(keyword)
    )
  }

  return result
})

// 同步选中的 Spider 到 formData
watch(selectedSpiderNames, (newVal) => {
  formData.value.tools = newVal.map((spiderName) => ({
    spider_name: spiderName,
  }))
})

// 加载 Spider 列表
const loadSpiders = async () => {
  loading.value = true
  try {
    await mcpStore.fetchAvailableSpiders()
  } finally {
    loading.value = false
  }
}

// 初始化表单
const initForm = () => {
  if (props.service) {
    formData.value = {
      name: props.service.name,
      display_name: props.service.display_name,
      description: props.service.description,
      transport: props.service.transport,
      tools: [],
    }
    // 加载服务工具列表
    loadServiceTools(props.service.id)
  } else {
    formData.value = {
      name: '',
      display_name: '',
      description: '',
      transport: 'http',
      tools: [],
    }
    selectedSpiderNames.value = []
  }
}

const loadServiceTools = async (serviceId: number) => {
  const tools = await mcpStore.fetchServiceTools(serviceId)
  selectedSpiderNames.value = tools.map((t) => t.spider_name)
}

const handleClose = () => {
  emit('update:modelValue', false)
  formRef.value?.resetFields()
  selectedSpiderNames.value = []
  spiderSearch.value = ''
  selectedPlatform.value = ''
}

// 处理平台变化
const handlePlatformChange = () => {
  // 平台变化时，清空搜索以避免混淆
  spiderSearch.value = ''
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (formData.value.tools.length === 0) {
    ElMessage.warning('请至少选择一个 Spider')
    return
  }

  submitting.value = true
  try {
    if (isEdit.value && props.service) {
      await mcpStore.updateService(props.service.id, formData.value)
      ElMessage.success('服务更新成功')
    } else {
      await mcpStore.createService(formData.value)
      ElMessage.success('服务创建成功')
    }
    emit('saved')
    handleClose()
  } catch (error: any) {
    console.error('保存服务失败:', error)
  } finally {
    submitting.value = false
  }
}

watch(() => props.modelValue, (val) => {
  if (val) {
    initForm()
    loadSpiders()
  }
})

onMounted(() => {
  if (props.modelValue) {
    loadSpiders()
  }
})
</script>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.tools-selector {
  width: 100%;

  .selector-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .selector-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .selector-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .spider-list {
    max-height: 300px;
    overflow-y: auto;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    padding: 8px;

    .spider-item {
      padding: 8px;
      border-radius: 4px;
      transition: background-color 0.2s;

      &:hover {
        background-color: #f5f7fa;
      }

      &:not(:last-child) {
        margin-bottom: 8px;
      }

      .spider-info {
        margin-left: 24px;

        .spider-name {
          display: flex;
          align-items: center;
          margin-bottom: 4px;
        }

        .spider-desc {
          font-size: 13px;
          color: #606266;
          margin-bottom: 4px;
        }

        .spider-params {
          font-size: 12px;
          color: #909399;
        }
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
