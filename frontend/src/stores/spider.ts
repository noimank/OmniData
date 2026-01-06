import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/spiders'
import type { SpiderInfo, SpiderResult, SpiderSchema } from '@/api/types'

export const useSpiderStore = defineStore('spider', () => {
  const spiders = ref<SpiderInfo[]>([])
  const currentSpider = ref<SpiderInfo | null>(null)
  const spiderSchema = ref<SpiderSchema | null>(null)
  const executionResult = ref<SpiderResult | null>(null)
  const loading = ref<boolean>(false)
  const running = ref<boolean>(false)

  // 获取爬虫列表
  const fetchSpiders = async () => {
    try {
      loading.value = true
      const result = await api.getSpiders()
      spiders.value = result.spiders
    } catch (error) {
      console.error('Failed to fetch spiders:', error)
    } finally {
      loading.value = false
    }
  }

  // 获取爬虫详情
  const fetchSpiderInfo = async (spiderName: string) => {
    try {
      const info = await api.getSpiderInfo(spiderName)
      const index = spiders.value.findIndex((s) => s.name === spiderName)
      if (index !== -1) {
        spiders.value[index] = info
      }
      return info
    } catch (error) {
      console.error('Failed to fetch spider info:', error)
      return null
    }
  }

  // 获取爬虫 schema
  const fetchSpiderSchema = async (spiderName: string) => {
    try {
      loading.value = true
      const schema = await api.getSpiderSchema(spiderName)
      spiderSchema.value = schema
      return schema
    } catch (error) {
      console.error('Failed to fetch spider schema:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  // 运行爬虫
  const runSpider = async (spiderName: string, params: Record<string, any>) => {
    try {
      running.value = true
      const result = await api.runSpider({ spider_name: spiderName, params })
      executionResult.value = result
      return result
    } catch (error) {
      console.error('Failed to run spider:', error)
      return null
    } finally {
      running.value = false
    }
  }

  // 批量运行爬虫
  const runSpiderBatch = async (
    spiderName: string,
    paramsList: Record<string, any>[],
    maxConcurrency = 3
  ) => {
    try {
      running.value = true
      const result = await api.runSpiderBatch({
        spider_name: spiderName,
        params_list: paramsList,
        max_concurrency: maxConcurrency
      })
      return result.results
    } catch (error) {
      console.error('Failed to run spider batch:', error)
      return []
    } finally {
      running.value = false
    }
  }

  // 验证参数
  const validateParams = async (spiderName: string, params: Record<string, any>) => {
    try {
      const result = await api.validateSpiderParams(spiderName, { params })
      return result
    } catch (error) {
      console.error('Failed to validate params:', error)
      return { valid: false, errors: [String(error)], warnings: [] }
    }
  }

  // 设置当前爬虫
  const setCurrentSpider = (spider: SpiderInfo | null) => {
    currentSpider.value = spider
    spiderSchema.value = null
    executionResult.value = null
  }

  // 清除执行结果
  const clearResult = () => {
    executionResult.value = null
  }

  return {
    spiders,
    currentSpider,
    spiderSchema,
    executionResult,
    loading,
    running,
    fetchSpiders,
    fetchSpiderInfo,
    fetchSpiderSchema,
    runSpider,
    runSpiderBatch,
    validateParams,
    setCurrentSpider,
    clearResult
  }
})
