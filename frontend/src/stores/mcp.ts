import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as mcpApi from '@/api/mcp'
import type {
  McpService,
  McpServiceCreate,
  McpServiceUpdate,
  McpTool,
  McpToolCreate,
  SpiderPrompt,
  SpiderPromptCreate,
  SpiderPromptUpdate,
  ToolPromptVersionResponse,
  ToolPromptVersionUpdate,
  SpiderInfoForMcp,
} from '@/api/types'

export const useMcpStore = defineStore('mcp', () => {
  // 状态
  const services = ref<McpService[]>([])
  const currentService = ref<McpService | null>(null)
  const serviceTools = ref<McpTool[]>([])
  const availableSpiders = ref<SpiderInfoForMcp[]>([])
  const spiderPrompts = ref<SpiderPrompt[]>([])
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  // ========== Spider 提示词管理 ==========

  const fetchSpiderPrompts = async (params?: { spider_name?: string; is_default?: boolean }) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.listSpiderPrompts(params)
      spiderPrompts.value = result
      return result
    } catch (err: any) {
      error.value = err.message || '获取提示词列表失败'
      console.error('Failed to fetch spider prompts:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const getSpiderPrompt = async (promptId: number): Promise<SpiderPrompt | null> => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.getSpiderPrompt(promptId)
      return result
    } catch (err: any) {
      error.value = err.message || '获取提示词详情失败'
      console.error('Failed to get spider prompt:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const createSpiderPrompt = async (data: SpiderPromptCreate) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.createSpiderPrompt(data)
      spiderPrompts.value.push(result)
      return result
    } catch (err: any) {
      error.value = err.message || '创建提示词失败'
      console.error('Failed to create spider prompt:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateSpiderPrompt = async (promptId: number, data: SpiderPromptUpdate) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.updateSpiderPrompt(promptId, data)
      const index = spiderPrompts.value.findIndex((p) => p.id === promptId)
      if (index !== -1) {
        spiderPrompts.value[index] = result
      }
      return result
    } catch (err: any) {
      error.value = err.message || '更新提示词失败'
      console.error('Failed to update spider prompt:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteSpiderPrompt = async (promptId: number) => {
    try {
      loading.value = true
      error.value = null
      await mcpApi.deleteSpiderPrompt(promptId)
      spiderPrompts.value = spiderPrompts.value.filter((p) => p.id !== promptId)
      return true
    } catch (err: any) {
      error.value = err.message || '删除提示词失败'
      console.error('Failed to delete spider prompt:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ========== 服务管理 ==========

  const fetchServices = async (isActive?: boolean) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.listMcpServices(isActive)
      services.value = result
      return result
    } catch (err: any) {
      error.value = err.message || '获取服务列表失败'
      console.error('Failed to fetch services:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const fetchService = async (serviceId: number) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.getMcpService(serviceId)
      currentService.value = result
      return result
    } catch (err: any) {
      error.value = err.message || '获取服务详情失败'
      console.error('Failed to fetch service:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const createService = async (data: McpServiceCreate) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.createMcpService(data)
      services.value.push(result)
      return result
    } catch (err: any) {
      error.value = err.message || '创建服务失败'
      console.error('Failed to create service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateService = async (serviceId: number, data: McpServiceUpdate) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.updateMcpService(serviceId, data)
      const index = services.value.findIndex((s) => s.id === serviceId)
      if (index !== -1) {
        services.value[index] = result
      }
      if (currentService.value?.id === serviceId) {
        currentService.value = result
      }
      return result
    } catch (err: any) {
      error.value = err.message || '更新服务失败'
      console.error('Failed to update service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deleteService = async (serviceId: number) => {
    try {
      loading.value = true
      error.value = null
      await mcpApi.deleteMcpService(serviceId)
      services.value = services.value.filter((s) => s.id !== serviceId)
      if (currentService.value?.id === serviceId) {
        currentService.value = null
      }
      return true
    } catch (err: any) {
      error.value = err.message || '删除服务失败'
      console.error('Failed to delete service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const activateService = async (serviceId: number) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.activateMcpService(serviceId)
      const index = services.value.findIndex((s) => s.id === serviceId)
      if (index !== -1) {
        services.value[index] = result
      }
      if (currentService.value?.id === serviceId) {
        currentService.value = result
      }
      return result
    } catch (err: any) {
      error.value = err.message || '激活服务失败'
      console.error('Failed to activate service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const deactivateService = async (serviceId: number) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.deactivateMcpService(serviceId)
      const index = services.value.findIndex((s) => s.id === serviceId)
      if (index !== -1) {
        services.value[index] = result
      }
      if (currentService.value?.id === serviceId) {
        currentService.value = result
      }
      return result
    } catch (err: any) {
      error.value = err.message || '停用服务失败'
      console.error('Failed to deactivate service:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ========== 工具管理 ==========

  const fetchServiceTools = async (serviceId: number) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.listTools(serviceId)
      serviceTools.value = result
      return result
    } catch (err: any) {
      error.value = err.message || '获取工具列表失败'
      console.error('Failed to fetch service tools:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const addTool = async (serviceId: number, data: McpToolCreate) => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.addTool(serviceId, data)
      serviceTools.value.push(result)
      return result
    } catch (err: any) {
      error.value = err.message || '添加工具失败'
      console.error('Failed to add tool:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const removeTool = async (serviceId: number, toolId: number) => {
    try {
      loading.value = true
      error.value = null
      await mcpApi.removeTool(serviceId, toolId)
      serviceTools.value = serviceTools.value.filter((t) => t.id !== toolId)
      return true
    } catch (err: any) {
      error.value = err.message || '移除工具失败'
      console.error('Failed to remove tool:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ========== 工具提示词版本管理 ==========

  const getToolPromptVersion = async (
    serviceId: number,
    toolId: number
  ): Promise<ToolPromptVersionResponse | null> => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.getToolPromptVersion(serviceId, toolId)
      return result
    } catch (err: any) {
      error.value = err.message || '获取工具提示词版本失败'
      console.error('Failed to get tool prompt version:', err)
      return null
    } finally {
      loading.value = false
    }
  }

  const setToolPromptVersion = async (
    serviceId: number,
    toolId: number,
    data: ToolPromptVersionUpdate
  ): Promise<ToolPromptVersionResponse | null> => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.setToolPromptVersion(serviceId, toolId, data)
      // 更新工具列表中的版本信息
      const toolIndex = serviceTools.value.findIndex((t) => t.id === toolId)
      if (toolIndex !== -1) {
        serviceTools.value[toolIndex].selected_prompt_version = result.current_version
        serviceTools.value[toolIndex].current_prompt_description = result.current_description
      }
      return result
    } catch (err: any) {
      error.value = err.message || '设置提示词版本失败'
      console.error('Failed to set tool prompt version:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  const clearToolPromptVersion = async (
    serviceId: number,
    toolId: number
  ): Promise<ToolPromptVersionResponse | null> => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.clearToolPromptVersion(serviceId, toolId)
      // 更新工具列表
      const toolIndex = serviceTools.value.findIndex((t) => t.id === toolId)
      if (toolIndex !== -1) {
        serviceTools.value[toolIndex].selected_prompt_version = null
        serviceTools.value[toolIndex].current_prompt_description = result.current_description
      }
      return result
    } catch (err: any) {
      error.value = err.message || '清除提示词版本失败'
      console.error('Failed to clear tool prompt version:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // ========== Spider 信息 ==========

  const fetchAvailableSpiders = async () => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.listAvailableSpiders()
      availableSpiders.value = result
      return result
    } catch (err: any) {
      error.value = err.message || '获取 Spider 列表失败'
      console.error('Failed to fetch available spiders:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  const fetchAvailableSpidersForPrompts = async () => {
    try {
      loading.value = true
      error.value = null
      const result = await mcpApi.listAvailableSpidersForPrompts()
      return result
    } catch (err: any) {
      error.value = err.message || '获取 Spider 列表失败'
      console.error('Failed to fetch available spiders for prompts:', err)
      return []
    } finally {
      loading.value = false
    }
  }

  // ========== 辅助方法 ==========

  const setCurrentService = (service: McpService | null) => {
    currentService.value = service
  }

  const clearError = () => {
    error.value = null
  }

  return {
    // 状态
    services,
    currentService,
    serviceTools,
    availableSpiders,
    spiderPrompts,
    loading,
    error,

    // Spider 提示词管理
    fetchSpiderPrompts,
    getSpiderPrompt,
    createSpiderPrompt,
    updateSpiderPrompt,
    deleteSpiderPrompt,

    // 服务管理
    fetchServices,
    fetchService,
    createService,
    updateService,
    deleteService,
    activateService,
    deactivateService,

    // 工具管理
    fetchServiceTools,
    addTool,
    removeTool,

    // 工具提示词版本管理
    getToolPromptVersion,
    setToolPromptVersion,
    clearToolPromptVersion,

    // Spider 信息
    fetchAvailableSpiders,
    fetchAvailableSpidersForPrompts,

    // 辅助方法
    setCurrentService,
    clearError,
  }
})
