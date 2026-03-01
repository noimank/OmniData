import request from './request'
import type {
  McpService,
  McpServiceCreate,
  McpServiceUpdate,
  McpTool,
  McpToolCreate,
  SpiderPrompt,
  SpiderPromptCreate,
  SpiderPromptUpdate,
  PromptUsageInfo,
  ToolPromptVersionResponse,
  ToolPromptVersionUpdate,
  SpiderInfoForMcp,
  ApiResponse
} from './types'

const MCP_BASE = '/v1/mcp-services'
const SPIDER_PROMPT_BASE = '/v1/spider-prompts'

// ============== Spider 提示词管理 ==============

export const listSpiderPrompts = (params?: {
  spider_name?: string
  is_default?: boolean
}): Promise<ApiResponse<SpiderPrompt[]>> => {
  const query = new URLSearchParams()
  if (params?.spider_name !== undefined) query.append('spider_name', params.spider_name)
  if (params?.is_default !== undefined) query.append('is_default', String(params.is_default))
  const queryString = query.toString()
  return request.get<ApiResponse<SpiderPrompt[]>>(`${SPIDER_PROMPT_BASE}${queryString ? `?${queryString}` : ''}`)
}

export const getSpiderPrompt = (promptId: number): Promise<ApiResponse<SpiderPrompt>> => {
  return request.get<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}/${promptId}`)
}

export const createSpiderPrompt = (data: SpiderPromptCreate): Promise<ApiResponse<SpiderPrompt>> => {
  return request.post<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}`, data)
}

export const updateSpiderPrompt = (promptId: number, data: SpiderPromptUpdate): Promise<ApiResponse<SpiderPrompt>> => {
  return request.put<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}/${promptId}`, data)
}

export const deleteSpiderPrompt = (promptId: number): Promise<ApiResponse<void>> => {
  return request.delete<ApiResponse<void>>(`${SPIDER_PROMPT_BASE}/${promptId}`)
}

export const setSpiderPromptAsDefault = (promptId: number): Promise<ApiResponse<SpiderPrompt>> => {
  return request.put<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}/${promptId}/set-default`)
}

export const getSpiderPromptUsage = (promptId: number): Promise<ApiResponse<PromptUsageInfo>> => {
  return request.get<ApiResponse<PromptUsageInfo>>(`${SPIDER_PROMPT_BASE}/${promptId}/usage`)
}

// Per-Spider 提示词端点

export const listSpiderPromptsByName = (spiderName: string): Promise<ApiResponse<SpiderPrompt[]>> => {
  return request.get<ApiResponse<SpiderPrompt[]>>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/prompts`)
}

export const createSpiderPromptForSpider = (
  spiderName: string,
  data: Omit<SpiderPromptCreate, 'spider_name'>
): Promise<ApiResponse<SpiderPrompt>> => {
  return request.post<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/prompts`, data)
}

export const getSpiderDefaultPrompt = (spiderName: string): Promise<ApiResponse<SpiderPrompt>> => {
  return request.get<ApiResponse<SpiderPrompt>>(`${SPIDER_PROMPT_BASE}/spiders/${spiderName}/default-prompt`)
}

// 获取所有可用的 Spider 列表（用于提示词管理）
export const listAvailableSpidersForPrompts = (): Promise<ApiResponse<SpiderInfoForMcp[]>> => {
  return request.get<ApiResponse<SpiderInfoForMcp[]>>(`${SPIDER_PROMPT_BASE}/spiders/available`)
}

// ============== 服务 CRUD ==============

export const listMcpServices = (isActive?: boolean): Promise<ApiResponse<McpService[]>> => {
  const params = isActive !== undefined ? `?is_active=${isActive}` : ''
  return request.get<ApiResponse<McpService[]>>(`${MCP_BASE}${params}`)
}

export const getMcpService = (serviceId: number): Promise<ApiResponse<McpService>> => {
  return request.get<ApiResponse<McpService>>(`${MCP_BASE}/${serviceId}`)
}

export const createMcpService = (data: McpServiceCreate): Promise<ApiResponse<McpService>> => {
  return request.post<ApiResponse<McpService>>(`${MCP_BASE}`, data)
}

export const updateMcpService = (serviceId: number, data: McpServiceUpdate): Promise<ApiResponse<McpService>> => {
  return request.put<ApiResponse<McpService>>(`${MCP_BASE}/${serviceId}`, data)
}

export const deleteMcpService = (serviceId: number): Promise<ApiResponse<void>> => {
  return request.delete<ApiResponse<void>>(`${MCP_BASE}/${serviceId}`)
}

export const activateMcpService = (serviceId: number): Promise<ApiResponse<McpService>> => {
  return request.put<ApiResponse<McpService>>(`${MCP_BASE}/${serviceId}/activate`, {})
}

export const deactivateMcpService = (serviceId: number): Promise<ApiResponse<McpService>> => {
  return request.put<ApiResponse<McpService>>(`${MCP_BASE}/${serviceId}/deactivate`, {})
}

// ============== 工具管理 ==============

export const listTools = (serviceId: number): Promise<ApiResponse<McpTool[]>> => {
  return request.get<ApiResponse<McpTool[]>>(`${MCP_BASE}/${serviceId}/tools`)
}

export const addTool = (serviceId: number, data: McpToolCreate): Promise<ApiResponse<McpTool>> => {
  return request.post<ApiResponse<McpTool>>(`${MCP_BASE}/${serviceId}/tools`, data)
}

export const removeTool = (serviceId: number, toolId: number): Promise<ApiResponse<void>> => {
  return request.delete<ApiResponse<void>>(`${MCP_BASE}/${serviceId}/tools/${toolId}`)
}

// ============== 工具提示词版本管理 ==============

export const getToolPromptVersion = (
  serviceId: number,
  toolId: number
): Promise<ApiResponse<ToolPromptVersionResponse>> => {
  return request.get<ApiResponse<ToolPromptVersionResponse>>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`)
}

export const setToolPromptVersion = (
  serviceId: number,
  toolId: number,
  data: ToolPromptVersionUpdate
): Promise<ApiResponse<ToolPromptVersionResponse>> => {
  return request.put<ApiResponse<ToolPromptVersionResponse>>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`, data)
}

export const clearToolPromptVersion = (
  serviceId: number,
  toolId: number
): Promise<ApiResponse<ToolPromptVersionResponse>> => {
  return request.delete<ApiResponse<ToolPromptVersionResponse>>(`${MCP_BASE}/${serviceId}/tools/${toolId}/prompt-version`)
}

// ============== Spider 信息 ==============

export const listAvailableSpiders = (): Promise<ApiResponse<SpiderInfoForMcp[]>> => {
  return request.get<ApiResponse<SpiderInfoForMcp[]>>(`${MCP_BASE}/spiders/available`)
}
