import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/monitor'
import type { BrowserContextPoolStats, SystemStats, ContextInfo } from '@/api/types'

export const useMonitorStore = defineStore('monitor', () => {
  const contextPool = ref<BrowserContextPoolStats | null>(null)
  const systemResource = ref<SystemStats | null>(null)
  const contextList = ref<ContextInfo[]>([])
  const loading = ref<boolean>(false)

  // 获取浏览器上下文池状态
  const fetchContextPool = async () => {
    try {
      contextPool.value = await api.getBrowserContextPool()
    } catch (error) {
      console.error('Failed to fetch context pool stats:', error)
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

  // 获取 Context 列表
  const fetchContextList = async () => {
    try {
      contextList.value = await api.getContextList()
    } catch (error) {
      console.error('Failed to fetch context list:', error)
    }
  }

  // 获取所有数据
  const fetchAll = async () => {
    loading.value = true
    try {
      await Promise.all([
        fetchContextPool(),
        fetchSystemResource(),
        fetchContextList()
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    contextPool,
    systemResource,
    contextList,
    loading,
    fetchContextPool,
    fetchSystemResource,
    fetchContextList,
    fetchAll
  }
})
