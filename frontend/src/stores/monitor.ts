import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/monitor'
import type { BrowserPoolStats, SpiderStats, SystemStats } from '@/api/types'

export const useMonitorStore = defineStore('monitor', () => {
  const browserPool = ref<BrowserPoolStats | null>(null)
  const spiderStats = ref<SpiderStats | null>(null)
  const systemResource = ref<SystemStats | null>(null)
  const loading = ref<boolean>(false)

  // 获取浏览器池状态
  const fetchBrowserPool = async () => {
    try {
      browserPool.value = await api.getBrowserPool()
    } catch (error) {
      console.error('Failed to fetch browser pool stats:', error)
    }
  }

  // 获取爬虫统计
  const fetchSpiderStats = async () => {
    try {
      spiderStats.value = await api.getSpiderStats()
    } catch (error) {
      console.error('Failed to fetch spider stats:', error)
    }
  }

  // 获取系统资源
  const fetchSystemResource = async () => {
    try {
      systemResource.value = await api.getSystemResource()
    } catch (error) {
      console.error('Failed to fetch system resource:', error)
    }
  }

  // 获取所有数据
  const fetchAll = async () => {
    loading.value = true
    try {
      await Promise.all([
        fetchBrowserPool(),
        fetchSpiderStats(),
        fetchSystemResource()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    browserPool,
    spiderStats,
    systemResource,
    loading,
    fetchBrowserPool,
    fetchSpiderStats,
    fetchSystemResource,
    fetchAll
  }
})
