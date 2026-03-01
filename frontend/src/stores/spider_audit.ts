import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/spider_audit'
import type { SpiderAuditRecord, SpiderAuditStats, SpiderAuditQuery } from '@/api/types'

export const useSpiderAuditStore = defineStore('spiderAudit', () => {
  // 状态
  const stats = ref<SpiderAuditStats | null>(null)
  const records = ref<SpiderAuditRecord[]>([])
  const totalRecords = ref(0)
  const platforms = ref<string[]>([])
  const spiders = ref<string[]>([])
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // 查询参数
  const queryParams = ref<SpiderAuditQuery>({
    page: 1,
    page_size: 20,
  })

  // ========== 统计信息 ==========

  const fetchStats = async () => {
    try {
      loading.value = true
      error.value = null
      const response = await api.getAuditStats()
      stats.value = response.data
      return stats.value
    } catch (err: any) {
      error.value = err.message || '获取统计信息失败'
      console.error('Failed to fetch audit stats:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ========== 审计记录 ==========

  const fetchRecords = async () => {
    try {
      loading.value = true
      error.value = null
      const response = await api.getAuditRecords(queryParams.value)
      if (response.data) {
        records.value = response.data.items || []
        totalRecords.value = response.data.count
      }
      return response.data
    } catch (err: any) {
      error.value = err.message || '获取审计记录失败'
      console.error('Failed to fetch audit records:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const setQueryParams = (params: Partial<SpiderAuditQuery>) => {
    queryParams.value = { ...queryParams.value, ...params }
    // 如果修改了筛选条件，重置到第一页
    if (
      params.spider_name !== undefined ||
      params.platform !== undefined ||
      params.success !== undefined ||
      params.start_date !== undefined ||
      params.end_date !== undefined
    ) {
      queryParams.value.page = 1
    }
  }

  const resetQueryParams = () => {
    queryParams.value = {
      page: 1,
      page_size: 20,
    }
  }

  // ========== 平台和爬虫列表 ==========

  const fetchPlatforms = async () => {
    try {
      const response = await api.getAuditPlatforms()
      platforms.value = response.data || []
      return platforms.value
    } catch (err: any) {
      console.error('Failed to fetch platforms:', err)
      return []
    }
  }

  const fetchSpiders = async (platform?: string) => {
    try {
      const response = await api.getAuditSpiders(platform)
      spiders.value = response.data || []
      return spiders.value
    } catch (err: any) {
      console.error('Failed to fetch spiders:', err)
      return []
    }
  }

  // ========== 辅助方法 ==========

  const clearError = () => {
    error.value = null
  }

  const refresh = async () => {
    await Promise.all([fetchStats(), fetchRecords()])
  }

  // ========== 删除和清理 ==========

  const deleteRecord = async (recordId: number) => {
    try {
      loading.value = true
      error.value = null
      await api.deleteAuditRecord(recordId)
      // 从本地列表中移除
      records.value = records.value.filter((r) => r.id !== recordId)
      totalRecords.value = Math.max(0, totalRecords.value - 1)
      return true
    } catch (err: any) {
      error.value = err.message || '删除记录失败'
      console.error('Failed to delete audit record:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const cleanupOldRecords = async (days: number = 30) => {
    try {
      loading.value = true
      error.value = null
      const response = await api.cleanupAuditRecords(days)
      // 刷新数据
      await Promise.all([fetchStats(), fetchRecords()])
      return response.data?.count || 0
    } catch (err: any) {
      error.value = err.message || '清理记录失败'
      console.error('Failed to cleanup audit records:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // 状态
    stats,
    records,
    totalRecords,
    platforms,
    spiders,
    loading,
    error,
    queryParams,

    // 方法
    fetchStats,
    fetchRecords,
    setQueryParams,
    resetQueryParams,
    fetchPlatforms,
    fetchSpiders,
    clearError,
    refresh,
    deleteRecord,
    cleanupOldRecords,
  }
})
