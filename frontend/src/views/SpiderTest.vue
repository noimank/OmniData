<template>
  <div class="spider-test-page">
    <el-row :gutter="20">
      <!-- 左侧：爬虫选择和参数配置 -->
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>爬虫测试</span>
              <el-button :icon="Refresh" @click="fetchSpiders" :loading="loading" />
            </div>
          </template>

          <!-- 平台筛选 -->
          <div class="platform-filter">
            <span class="filter-label">平台筛选：</span>
            <el-select
              v-model="selectedPlatform"
              placeholder="全部平台"
              @change="handlePlatformChange"
              clearable
              style="flex: 1; max-width: 200px"
            >
              <el-option
                v-for="platform in platforms"
                :key="platform"
                :label="platform"
                :value="platform"
              />
            </el-select>
          </div>

          <!-- 爬虫选择（支持搜索） -->
          <el-select
            v-model="selectedSpiderName"
            placeholder="请选择爬虫，支持搜索"
            @change="handleSpiderChange"
            style="width: 100%; margin-bottom: 20px"
            filterable
            :filter-method="filterSpiders"
            :loading="loading"
            clearable
          >
            <el-option
              v-for="spider in filteredSpiders"
              :key="spider.name"
              :label="`${spider.name} - ${spider.description}`"
              :value="spider.name"
            >
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px">
                <span>{{ spider.name }}</span>
                <div style="display: flex; gap: 4px">
                  <el-tag size="small" type="info">{{ spider.platform }}</el-tag>
                </div>
              </div>
            </el-option>
          </el-select>

          <!-- 爬虫信息 -->
          <el-descriptions v-if="currentSpider" :column="1" border size="small" class="mb-20">
            <el-descriptions-item label="名称">{{ currentSpider.name }}</el-descriptions-item>
            <el-descriptions-item label="描述">{{ currentSpider.description }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ currentSpider.version }}</el-descriptions-item>
          </el-descriptions>

          <!-- 参数配置表单 -->
          <div v-if="spiderSchema && Object.keys(spiderSchema.params_schema).length > 0">
            <h4 class="form-title">参数配置</h4>
            <el-form :model="spiderParams" label-width="100px" size="small">
              <el-form-item
                v-for="(schema, key) in spiderSchema.params_schema"
                :key="key"
                :label="schema.title || key"
                :required="spiderSchema.required?.includes(key)"
              >
                <!-- 参数描述提示 -->
                <template #label>
                  <span>{{ schema.title || key }}</span>
                  <el-tooltip
                    v-if="schema.description"
                    :content="schema.description"
                    placement="top"
                    :show-after="300"
                  >
                    <el-icon class="param-tooltip"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </template>

                <!-- 枚举类型 -->
                <el-select
                  v-if="schema.enum"
                  v-model="spiderParams[key]"
                  :placeholder="`请选择${schema.title || key}`"
                  style="width: 100%"
                >
                  <el-option
                    v-for="opt in schema.enum"
                    :key="opt"
                    :label="opt"
                    :value="opt"
                  />
                </el-select>
                <!-- 字符串类型 -->
                <el-input
                  v-else-if="schema.type === 'string'"
                  v-model="spiderParams[key]"
                  :placeholder="schema.description || `请输入${schema.title || key}`"
                  :type="key.includes('password') || key.includes('secret') ? 'password' : 'text'"
                />
                <!-- 数字类型 -->
                <el-input-number
                  v-else-if="schema.type === 'number' || schema.type === 'integer'"
                  v-model="spiderParams[key]"
                  :placeholder="schema.description || `请输入${schema.title || key}`"
                  style="width: 100%"
                />
                <!-- 布尔类型 -->
                <el-switch
                  v-else-if="schema.type === 'boolean'"
                  v-model="spiderParams[key]"
                />
                <!-- 默认 -->
                <el-input
                  v-else
                  v-model="spiderParams[key]"
                  :placeholder="schema.description || `请输入${schema.title || key}`"
                />
              </el-form-item>
            </el-form>

            <el-button
              type="primary"
              @click="handleRunSpider"
              :loading="running"
              :disabled="!selectedSpiderName"
              style="width: 100%; margin-top: 10px"
            >
              运行爬虫
            </el-button>
          </div>

          <!-- 无参数 -->
          <div v-else-if="currentSpider && !schemaLoading">
            <el-empty description="该爬虫无需配置参数">
              <el-button
                type="primary"
                @click="handleRunSpider"
                :loading="running"
              >
                运行爬虫
              </el-button>
            </el-empty>
          </div>

          <el-empty v-else-if="!selectedSpiderName" description="请选择爬虫" />
          <div v-else class="schema-loading">
            <el-icon class="is-loading" :size="32">
              <Loading />
            </el-icon>
            <p>加载参数配置中...</p>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：执行结果 -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>执行结果</span>
              <div>
                <el-button
                  v-if="executionResult"
                  type="primary"
                  size="small"
                  :icon="VideoPlay"
                  @click="handleRunSpider"
                  :loading="running"
                >
                  重新执行
                </el-button>
                <el-button
                  v-if="executionResult"
                  size="small"
                  :icon="Delete"
                  @click="handleClearResult"
                >
                  清除
                </el-button>
              </div>
            </div>
          </template>

          <!-- 运行中 -->
          <div v-if="running" class="running-status">
            <el-icon class="is-loading" :size="48">
              <Loading />
            </el-icon>
            <p>爬虫运行中...</p>
          </div>

          <!-- 执行结果 -->
          <div v-else-if="executionResult" class="result-content">
            <el-descriptions :column="2" border size="small" class="mb-20">
              <el-descriptions-item label="爬虫名称">
                {{ executionResult.spider_name }}
              </el-descriptions-item>
              <el-descriptions-item label="执行状态">
                <el-tag :type="executionResult.success ? 'success' : 'danger'">
                  {{ executionResult.success ? '成功' : '失败' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="开始时间">
                {{ formatDateTime(executionResult.started_at) }}
              </el-descriptions-item>
              <el-descriptions-item label="耗时">
                {{ executionResult.duration_seconds?.toFixed(2) || 0 }} 秒
              </el-descriptions-item>
            </el-descriptions>

            <!-- 消息信息 -->
            <el-alert
              v-if="executionResult.message"
              type="info"
              :title="executionResult.message"
              :closable="false"
              class="mb-20"
            />

            <!-- 错误信息 -->
            <el-alert
              v-if="!executionResult.success && executionResult.error"
              type="error"
              :title="executionResult.error"
              :closable="false"
              class="mb-20"
            />

            <!-- 数据展示 -->
            <div class="data-section">
              <h4>返回数据</h4>
              <el-scrollbar height="400">
                <pre class="json-result">{{ formatJson(executionResult.data) }}</pre>
              </el-scrollbar>
            </div>
          </div>

          <!-- 无结果 -->
          <el-empty v-else description="请选择爬虫并运行" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSpiderStore } from '@/stores/spider'
import type { SpiderInfo, ParamSchema } from '@/api/types'
import { Refresh, Loading, VideoPlay, Delete, QuestionFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const spiderStore = useSpiderStore()

const spiders = computed(() => spiderStore.spiders)
const currentSpider = computed(() => spiderStore.currentSpider)
const spiderSchema = computed(() => spiderStore.spiderSchema)
const executionResult = computed(() => spiderStore.executionResult)
const loading = computed(() => spiderStore.loading)
const running = computed(() => spiderStore.running)
const schemaLoading = ref(false)

// 平台筛选相关
const selectedPlatform = ref('')
const searchKeyword = ref('')

// 获取所有平台列表（去重并排序）
const platforms = computed(() => {
  const platformSet = new Set<string>()
  spiders.value.forEach((spider: SpiderInfo) => {
    if (spider.platform) {
      platformSet.add(spider.platform)
    }
  })
  return Array.from(platformSet).sort()
})

// 根据选中的平台和关键词过滤爬虫列表
const filteredSpiders = computed(() => {
  let result = spiders.value

  // 平台筛选
  if (selectedPlatform.value) {
    result = result.filter((spider: SpiderInfo) => spider.platform === selectedPlatform.value)
  }

  // 关键词筛选
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter((spider: SpiderInfo) =>
      spider.name.toLowerCase().includes(keyword) ||
      spider.description?.toLowerCase().includes(keyword) ||
      spider.platform?.toLowerCase().includes(keyword)
    )
  }

  return result
})

// 搜索方法（供 el-select filter-method 使用）
const filterSpiders = (keyword: string) => {
  searchKeyword.value = keyword
}

const selectedSpiderName = ref('')
const spiderParams = ref<Record<string, any>>({})

const fetchSpiders = async () => {
  await spiderStore.fetchSpiders()
}

const handlePlatformChange = () => {
  // 切换平台时清空选中的爬虫和搜索关键词
  selectedSpiderName.value = ''
  searchKeyword.value = ''
  spiderStore.setCurrentSpider(null)
}

const handleSpiderChange = async (spiderName: string) => {
  const spider = filteredSpiders.value.find((s: SpiderInfo) => s.name === spiderName)
  if (spider) {
    spiderStore.setCurrentSpider(spider)
    schemaLoading.value = true
    try {
      const schema = await spiderStore.fetchSpiderSchema(spiderName)
      // 初始化参数值
      spiderParams.value = {}
      if (schema) {
        Object.entries(schema.params_schema).forEach(([key, config]: [string, ParamSchema]) => {
          if (config.default !== undefined) {
            spiderParams.value[key] = config.default
          } else if (config.type === 'boolean') {
            spiderParams.value[key] = false
          } else if (config.type === 'number' || config.type === 'integer') {
            spiderParams.value[key] = 0
          } else {
            spiderParams.value[key] = ''
          }
        })
      }
    } finally {
      schemaLoading.value = false
    }
  }
}

const handleRunSpider = async () => {
  if (!selectedSpiderName.value) {
    ElMessage.warning('请选择爬虫')
    return
  }

  // 先进行参数验证
  const validationResult = await spiderStore.validateParams(selectedSpiderName.value, spiderParams.value)
  if (!validationResult.valid) {
    ElMessage.error(`参数验证失败：${validationResult.errors.join('；')}`)
    return
  }

  // 显示警告信息（如果有）
  if (validationResult.warnings && validationResult.warnings.length > 0) {
    ElMessage.warning(`参数警告：${validationResult.warnings.join('；')}`)
  }

  // 验证通过，执行爬虫
  const result = await spiderStore.runSpider(selectedSpiderName.value, spiderParams.value)
  if (result) {
    if (result.success) {
      ElMessage.success('执行成功')
    } else {
      ElMessage.error('执行失败')
    }
  }
}

const handleClearResult = () => {
  spiderStore.clearResult()
}

const formatDateTime = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const formatJson = (data: any) => {
  return JSON.stringify(data, null, 2)
}

onMounted(() => {
  fetchSpiders()
})
</script>

<style scoped lang="scss">
.spider-test-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
  }

  .mb-20 {
    margin-bottom: 20px;
  }

  .platform-filter {
    display: flex;
    align-items: center;
    margin-bottom: 16px;

    .filter-label {
      font-size: 14px;
      color: #606266;
      margin-right: 12px;
      white-space: nowrap;
    }
  }

  .form-title {
    margin: 0 0 16px 0;
    font-size: 14px;
    color: #606266;
  }

  .param-tooltip {
    margin-left: 4px;
    color: #909399;
    cursor: pointer;
    vertical-align: middle;

    &:hover {
      color: #409eff;
    }
  }

  .schema-loading {
    text-align: center;
    padding: 40px;
    color: #909399;
  }

  .running-status {
    text-align: center;
    padding: 60px;
    color: #409eff;
  }

  .result-content {
    .data-section {
      h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        color: #606266;
      }

      .json-result {
        margin: 0;
        padding: 16px;
        background-color: #f5f7fa;
        border-radius: 4px;
        font-size: 12px;
        line-height: 1.5;
        color: #303133;
        overflow-x: auto;
      }
    }
  }
}
</style>
